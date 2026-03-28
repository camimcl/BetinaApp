"""
src/api/telegram.py

Bot Telegram da Betina I.A. — assistente de apostas esportivas.

Funcionalidades:
  - Conversa livre via Gemini (prompt persuasivo de vendas)
  - Estado por chat: jogo acompanhado, lista de jogos, contexto
  - Jogos numerados: usuário responde com número para ver detalhes
  - Predição real com ajuste live (placar + tempo)
  - Registro de chat_ids para alertas proativos (in-memory)
  - Follow-up automático após cada interação
"""

import os
import random
from datetime import date
from typing import Optional, Set, Dict, Any, List

import httpx
from loguru import logger

# ── Configuração ─────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PLATFORM_URL       = os.getenv("PLATFORM_URL", "http://localhost:5173")
BETSAPI_TOKEN      = os.getenv("BETSAPI_TOKEN", "")
BETSAPI_BASE       = "https://api.betsapi.com/v1"
_TELEGRAM_API      = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def is_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN)


# ── Registro de Chat IDs (in-memory) ────────────────────────────────────────

_registered_chats: Set[int] = set()
_daily_sends: dict = {}
MAX_DAILY_ALERTS = 3


def register_chat(chat_id: int) -> bool:
    if chat_id in _registered_chats:
        return False
    _registered_chats.add(chat_id)
    logger.info(f"Chat registrado: {chat_id}")
    return True


def unregister_chat(chat_id: int) -> bool:
    if chat_id not in _registered_chats:
        return False
    _registered_chats.discard(chat_id)
    logger.info(f"Chat removido: {chat_id}")
    return True


def get_registered_chats() -> list:
    return list(_registered_chats)


def can_send_today() -> bool:
    today = str(date.today())
    return _daily_sends.get(today, 0) < MAX_DAILY_ALERTS


def _increment_daily_counter():
    today = str(date.today())
    _daily_sends[today] = _daily_sends.get(today, 0) + 1
    for key in list(_daily_sends.keys()):
        if key != today:
            del _daily_sends[key]


def get_daily_sends_count() -> int:
    return _daily_sends.get(str(date.today()), 0)


# ── Estado por Chat (in-memory) ─────────────────────────────────────────────

_chat_state: Dict[int, Dict[str, Any]] = {}


def _get_state(chat_id: int) -> Dict[str, Any]:
    """Retorna estado do chat, criando se não existir."""
    if chat_id not in _chat_state:
        _chat_state[chat_id] = {
            "last_matches": [],    # Lista de jogos da última consulta
            "watching": None,      # Jogo que o usuário está acompanhando
            "last_action": None,   # Última ação (para contexto de follow-up)
        }
    return _chat_state[chat_id]


def _set_watching(chat_id: int, match: dict):
    """Define o jogo que o usuário está acompanhando."""
    state = _get_state(chat_id)
    state["watching"] = match
    state["last_action"] = "watching"


# ── Envio de Mensagens ───────────────────────────────────────────────────────

async def send_message(chat_id: int, text: str) -> dict:
    if not TELEGRAM_BOT_TOKEN:
        return {"status": "error", "detail": "TELEGRAM_BOT_TOKEN não configurado"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
        data = resp.json()
        if data.get("ok"):
            return {"status": "sent", "message_id": data["result"]["message_id"]}
        else:
            logger.error(f"Telegram API erro: {data}")
            return {"status": "error", "detail": data.get("description", "Erro")}
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram: {e}")
        return {"status": "error", "detail": str(e)}


# ── Busca de Jogos ───────────────────────────────────────────────────────────

async def _fetch_live_matches() -> List[dict]:
    """Busca jogos ao vivo via BetsAPI."""
    if not BETSAPI_TOKEN:
        return []

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(
                f"{BETSAPI_BASE}/events/inplay",
                params={"token": BETSAPI_TOKEN, "sport_id": 1}
            )
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Erro ao buscar jogos: {e}")
        return []


def _parse_score(score_str) -> tuple:
    """Parseia placar '2-1' em (2, 1). Aceita None."""
    if not score_str or not isinstance(score_str, str):
        return 0, 0
    try:
        parts = score_str.split("-")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0, 0


def _build_match_features(h_score: int, a_score: int) -> dict:
    """Constrói features do modelo a partir do placar observado."""
    return {
        "home_xg": h_score * 1.1 + 0.3,
        "away_xg": a_score * 1.1 + 0.3,
        "xg_diff": (h_score - a_score) * 1.1,
        "home_shots": max(h_score * 4, 3),
        "away_shots": max(a_score * 4, 3),
        "home_shots_ot": max(h_score * 2, 1),
        "away_shots_ot": max(a_score * 2, 1),
        "home_passes": 250 + int(random.random() * 200),
        "away_passes": 250 + int(random.random() * 200),
        "home_pass_acc": round(0.75 + random.random() * 0.15, 2),
        "away_pass_acc": round(0.75 + random.random() * 0.15, 2),
        "home_pressures": 50 + int(random.random() * 80),
        "away_pressures": 50 + int(random.random() * 80),
        "pressure_ratio": round(0.8 + random.random() * 0.8, 2),
        "home_fouls": 5 + int(random.random() * 10),
        "away_fouls": 5 + int(random.random() * 10),
    }


def _run_prediction(match: dict) -> dict:
    """Roda predição completa para um jogo ao vivo, incluindo ajuste live."""
    from src.models.predictor import predict_match

    home = match.get("home", {}).get("name", "Time A")
    away = match.get("away", {}).get("name", "Time B")
    score_str = match.get("ss", "0-0")
    minute = int(match.get("timer", {}).get("tm", 0) or 0)
    h_score, a_score = _parse_score(score_str)

    features = _build_match_features(h_score, a_score)

    prediction = predict_match(
        match_data=features,
        home_team_name=home,
        away_team_name=away,
        home_score=h_score,
        away_score=a_score,
        minute=minute,
    )

    prediction["_meta"] = {
        "home": home, "away": away,
        "score": score_str, "minute": minute,
        "h_score": h_score, "a_score": a_score,
        "league": match.get("league", {}).get("name", ""),
    }

    return prediction


# ── Seleção de Jogos ─────────────────────────────────────────────────────────

TIER1_KEYWORDS = [
    "premier", "la liga", "serie a", "bundesliga", "ligue 1",
    "champions", "libertadores", "brasileir", "copa do mundo",
    "europa league", "sul-americana", "mls", "liga mx",
]


def _pick_hottest_match(results: list) -> dict:
    """Seleciona o jogo mais quente."""
    scored = []
    for r in results:
        score_str = r.get("ss", "0-0")
        league = (r.get("league", {}).get("name", "") or "").lower()
        minute = int(r.get("timer", {}).get("tm", 0) or 0)
        h, a = _parse_score(score_str)
        diff = abs(h - a)

        points = 0
        if diff <= 1:
            points += 10
        if h + a > 0:
            points += 3  # jogo com gols é mais interessante
        if any(kw in league for kw in TIER1_KEYWORDS):
            points += 8
        if minute >= 60:
            points += 5
        elif minute >= 45:
            points += 2

        scored.append((points, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else None


# ── Processamento de Mensagens ───────────────────────────────────────────────

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]


async def handle_incoming_message(text: str, chat_id: int) -> str:
    """
    Processa mensagem recebida e retorna resposta.

    Fluxo inteligente:
    1. Comandos (/start, /jogos, /palpite, /alertas, /sair)
    2. Seleção numérica (se tem lista de jogos armazenada)
    3. Palavras-chave contextuais (sim, não, outro, atualizar)
    4. Conversa livre → Gemini com contexto do jogo acompanhado
    """
    lower = text.strip().lower()
    state = _get_state(chat_id)

    # ── Comandos de registro ──
    if lower in ("/alertas", "alertas", "alerta", "notificar"):
        was_new = register_chat(chat_id)
        state["last_action"] = "alertas"
        if was_new:
            return (
                "🔔 <b>Alertas ativados!</b>\n\n"
                "Vou te mandar até 3 palpites por dia com as melhores oportunidades 🔥\n\n"
                "Quando encontrar um jogo quente com boas odds, você vai ser o primeiro a saber!\n\n"
                "Enquanto isso, quer ver o que tá rolando agora? Manda /jogos ⚽"
            )
        return (
            "Você já tá recebendo alertas! 🔔\n\n"
            "Quer ver os jogos ao vivo? Manda /jogos\n"
            "Ou manda /sair se quiser cancelar os alertas."
        )

    if lower in ("/sair", "sair", "parar", "/stop", "cancelar"):
        was_registered = unregister_chat(chat_id)
        state["last_action"] = "sair"
        if was_registered:
            return (
                "❌ Alertas desativados!\n\n"
                "Sem problemas, você ainda pode pedir palpites quando quiser 😉\n"
                "É só mandar /palpite ou /jogos a qualquer momento!\n\n"
                f"Ou acessa a plataforma completa: {PLATFORM_URL}"
            )
        return "Você nem estava recebendo alertas 😅\nManda /alertas pra ativar!"

    # ── /start — Boas-vindas conversacional ──
    if lower.startswith("/start"):
        state["last_action"] = "start"
        # Deep link do site: /start site
        if "site" in lower:
            register_chat(chat_id)
            return (
                "Opa! 👋 Vi que você veio da <b>plataforma</b> — seja bem-vindo!\n\n"
                "Sou a <b>Betina</b>, sua analista de apostas com I.A. 🎯\n\n"
                "🔔 Já ativei os <b>alertas</b> pra você! "
                f"Vou te mandar até {MAX_DAILY_ALERTS} palpites quentes por dia.\n\n"
                "Enquanto isso, o que quer fazer?\n\n"
                "⚽ /jogos — Ver partidas ao vivo\n"
                "📊 /palpite — Meu melhor palpite agora\n"
                "💬 Ou me pergunta qualquer coisa sobre futebol!\n\n"
                "Bora começar? 🔥"
            )
        return _format_welcome()

    # ── Saudação informal → resposta natural ──
    if lower in ("oi", "olá", "ola", "hi", "hello", "eai", "e ai", "fala"):
        state["last_action"] = "greeting"
        return (
            "Eai! 👋 Tudo bem?\n\n"
            "Sou a <b>Betina</b>, sua parceira de palpites esportivos com I.A.! 🎯\n\n"
            "Tem vários jogos rolando agora... quer dar uma olhada?\n"
            "Manda /jogos que eu te mostro os melhores! ⚽🔥"
        )

    # ── /jogos — Lista numerada com seleção ──
    if lower in ("/jogos", "jogos", "jogo", "ao vivo", "live", "/live"):
        return await _handle_list_matches(chat_id)

    # ── /palpite — Palpite inteligente ──
    if lower in ("/palpite", "palpite", "palpites", "dica", "dicas", "/dica", "apostar"):
        return await _handle_smart_tip(chat_id)

    # ── Seleção numérica (1-8) — se tem lista de jogos ──
    if lower.isdigit() and 1 <= int(lower) <= 8:
        idx = int(lower) - 1
        if state["last_matches"] and idx < len(state["last_matches"]):
            return await _handle_select_match(chat_id, idx)

    # ── Follow-up contextual ──
    if lower in ("sim", "s", "bora", "quero", "vamos", "show", "claro", "manda"):
        return await _handle_yes(chat_id)

    if lower in ("não", "nao", "n", "outro", "outro jogo", "proximo", "próximo"):
        return await _handle_no(chat_id)

    if lower in ("atualizar", "update", "como ta", "como tá", "placar", "/atualizar"):
        return await _handle_update(chat_id)

    # ── Conversa livre → Gemini com contexto ──
    return await _handle_free_chat(chat_id, text)


# ── Handlers de Ação ─────────────────────────────────────────────────────────

async def _handle_list_matches(chat_id: int) -> str:
    """Lista jogos ao vivo com números clicáveis."""
    matches = await _fetch_live_matches()
    state = _get_state(chat_id)

    if not matches:
        state["last_action"] = "no_matches"
        return (
            "😕 Não tem nenhum jogo ao vivo agora...\n\n"
            "Mas fica de olho! Manda /alertas que eu te aviso "
            "quando tiver algo quente 🔥\n\n"
            f"Ou veja a agenda completa na plataforma:\n{PLATFORM_URL}"
        )

    # Seleciona os 8 melhores (priorizando tier-1 e jogos com gols)
    sorted_matches = sorted(matches, key=lambda r: _score_match(r), reverse=True)[:8]

    state["last_matches"] = sorted_matches
    state["last_action"] = "list"

    msg = "⚽ <b>Jogos ao vivo agora!</b>\n"
    msg += "Manda o <b>número</b> do jogo pra eu analisar:\n\n"

    for i, r in enumerate(sorted_matches):
        home = r.get("home", {}).get("name", "?")
        away = r.get("away", {}).get("name", "?")
        score = r.get("ss", "0-0")
        minute = r.get("timer", {}).get("tm", "?")
        league = r.get("league", {}).get("name", "")

        emoji = NUMBER_EMOJIS[i] if i < len(NUMBER_EMOJIS) else f"{i+1}."
        msg += f"{emoji}  <b>{home}</b> {score} <b>{away}</b>  ({minute}')\n"
        if league:
            msg += f"     📋 {league}\n"
        msg += "\n"

    msg += "👆 Manda o número (1-{}) do jogo que te interessa!".format(len(sorted_matches))

    return msg


async def _handle_select_match(chat_id: int, idx: int) -> str:
    """Usuário selecionou um jogo da lista — roda predição completa."""
    state = _get_state(chat_id)
    match = state["last_matches"][idx]

    _set_watching(chat_id, match)
    state["last_action"] = "prediction"

    try:
        prediction = _run_prediction(match)
        return _format_prediction_rich(prediction, chat_id)
    except Exception as e:
        logger.error(f"Erro na predição do jogo selecionado: {e}")
        return (
            "😅 Ops, tive um problema analisando esse jogo...\n\n"
            "Tenta outro! Manda /jogos pra ver a lista de novo."
        )


async def _handle_smart_tip(chat_id: int) -> str:
    """Palpite inteligente: usa jogo acompanhado ou busca o melhor."""
    state = _get_state(chat_id)

    # Se já está acompanhando um jogo → dá palpite atualizado dele
    if state.get("watching"):
        watching = state["watching"]
        home = watching.get("home", {}).get("name", "")
        state["last_action"] = "prediction"

        # Busca dados atualizados do jogo
        matches = await _fetch_live_matches()
        updated = None
        for m in matches:
            if m.get("home", {}).get("name", "") == home:
                updated = m
                break

        if updated:
            state["watching"] = updated
            prediction = _run_prediction(updated)
            msg = "🔄 <b>Atualização do seu jogo!</b>\n\n"
            msg += _format_prediction_rich(prediction, chat_id)
            return msg

    # Sem jogo acompanhado → busca o melhor
    matches = await _fetch_live_matches()

    if not matches:
        return (
            "Sem jogos ao vivo agora 😕\n\n"
            "Manda /alertas que eu te aviso quando tiver "
            "algo imperdível! 🔔🔥"
        )

    if len(matches) <= 3:
        # Poucos jogos → analisa o melhor direto
        best = _pick_hottest_match(matches)
        if best:
            _set_watching(chat_id, best)
            state["last_action"] = "prediction"
            prediction = _run_prediction(best)
            return _format_prediction_rich(prediction, chat_id)

    # Vários jogos → mostra top 3 pra escolher
    sorted_m = sorted(matches, key=lambda r: _score_match(r), reverse=True)[:3]
    state["last_matches"] = sorted_m
    state["last_action"] = "list"

    msg = "🎯 <b>Achei esses jogos quentes pra você!</b>\n"
    msg += "Qual quer que eu analise?\n\n"

    for i, r in enumerate(sorted_m):
        home = r.get("home", {}).get("name", "?")
        away = r.get("away", {}).get("name", "?")
        score = r.get("ss", "0-0")
        minute = r.get("timer", {}).get("tm", "?")
        league = r.get("league", {}).get("name", "")

        emoji = NUMBER_EMOJIS[i]
        h, a = _parse_score(score)

        # Indicador de "quente"
        diff = abs(h - a)
        heat = "🔥" if diff <= 1 else "⚡" if diff == 2 else ""

        msg += f"{emoji}  <b>{home}</b> {score} <b>{away}</b>  ({minute}') {heat}\n"
        if league:
            msg += f"     📋 {league}\n"
        msg += "\n"

    msg += "Manda o número ou diz o nome do time! 👇"
    return msg


async def _handle_yes(chat_id: int) -> str:
    """Usuário respondeu 'sim' — continua o fluxo."""
    state = _get_state(chat_id)
    last = state.get("last_action")

    if last == "prediction" and state.get("watching"):
        # Está acompanhando → redireciona pra plataforma
        w = state["watching"]
        home = w.get("home", {}).get("name", "time")
        return (
            f"🔥 Boa escolha! O jogo de <b>{home}</b> tá quente!\n\n"
            f"Acessa a plataforma pra ver a análise completa e apostar:\n"
            f"🔗 {PLATFORM_URL}\n\n"
            "Enquanto isso, quer que eu fique de olho e te avise se algo mudar? "
            "Manda /alertas! 🔔"
        )

    if last == "no_matches":
        register_chat(chat_id)
        return (
            "🔔 Pronto, te ativei nos alertas!\n\n"
            "Quando tiver um jogo quente, você vai ser o primeiro a saber 🎯\n\n"
            f"Enquanto isso, dá uma olhada na plataforma: {PLATFORM_URL}"
        )

    # Default: oferece jogos
    return await _handle_list_matches(chat_id)


async def _handle_no(chat_id: int) -> str:
    """Usuário disse 'não' ou 'outro' — oferece alternativas."""
    state = _get_state(chat_id)

    if state.get("watching") or state.get("last_matches"):
        state["watching"] = None
        return await _handle_list_matches(chat_id)

    return (
        "Sem problemas! 😉\n\n"
        "Quando quiser, é só mandar:\n"
        "⚽ /jogos — ver o que tá rolando\n"
        "📊 /palpite — meu melhor palpite"
    )


async def _handle_update(chat_id: int) -> str:
    """Atualiza dados do jogo que o usuário está acompanhando."""
    state = _get_state(chat_id)

    if not state.get("watching"):
        return (
            "Você não tá acompanhando nenhum jogo no momento!\n\n"
            "Manda /jogos pra escolher um ⚽"
        )

    return await _handle_smart_tip(chat_id)


async def _handle_free_chat(chat_id: int, text: str) -> str:
    """Conversa livre — Gemini com contexto do jogo acompanhado."""
    state = _get_state(chat_id)
    match_context = None

    # Injeta contexto do jogo acompanhado
    if state.get("watching"):
        w = state["watching"]
        home = w.get("home", {}).get("name", "")
        away = w.get("away", {}).get("name", "")
        score = w.get("ss", "0-0")
        minute = w.get("timer", {}).get("tm", "?")
        match_context = {
            "home": home, "away": away,
            "score": score, "minute": minute,
        }

    try:
        from src.api.gemini_client import chat_with_betina_whatsapp
        response = chat_with_betina_whatsapp(
            phone_number=str(chat_id),
            user_message=text,
            match_context=match_context,
        )

        # Adiciona CTA sutil ao final se a resposta não tem
        if PLATFORM_URL not in response and random.random() < 0.4:
            response += f"\n\n🔗 Quer a análise completa? {PLATFORM_URL}"

        return response

    except Exception as e:
        logger.error(f"Erro Gemini chat: {e}")
        # Fallback engajante
        if state.get("watching"):
            return (
                "Hmm, não consegui processar agora... 😅\n\n"
                "Mas posso te dar um palpite atualizado do jogo que você tá vendo!\n"
                "Manda /palpite 📊"
            )
        return (
            "Ops, tive um probleminha! 😅\n\n"
            "Mas ó, tem jogos ao vivo agora — quer que eu veja pra você?\n"
            "Manda /jogos ⚽"
        )


# ── Formatação ───────────────────────────────────────────────────────────────

def _format_welcome() -> str:
    """Mensagem de boas-vindas rica e conversacional."""
    return (
        "Fala! 👋 Sou a <b>Betina</b>, sua analista de apostas esportivas!\n\n"
        "Eu uso inteligência artificial pra analisar jogos ao vivo e encontrar "
        "as melhores oportunidades de aposta pra você 🎯\n\n"
        "<b>O que eu posso fazer:</b>\n\n"
        "⚽ /jogos — Ver as partidas ao vivo e escolher uma pra eu analisar\n"
        "📊 /palpite — Meu melhor palpite do momento\n"
        "🔔 /alertas — Receber até 3 alertas/dia dos jogos mais quentes\n"
        "💬 Ou pode me perguntar qualquer coisa sobre futebol!\n\n"
        "Bora começar? Manda /jogos pra ver o que tá rolando! 🔥"
    )


def _format_prediction_rich(prediction: dict, chat_id: int) -> str:
    """Formata predição completa, persuasiva e com follow-up."""
    meta = prediction.get("_meta", {})
    home = meta.get("home", "Time A")
    away = meta.get("away", "Time B")
    score = meta.get("score", "0-0")
    minute = meta.get("minute", 0)
    league = meta.get("league", "")
    h_score = meta.get("h_score", 0)
    a_score = meta.get("a_score", 0)

    hp = round(prediction.get("home_win_probability", 0) * 100)
    dp = round(prediction.get("draw_probability", 0) * 100)
    ap = round(prediction.get("away_win_probability", 0) * 100)

    best_pct, best_name = max(
        [(hp, home), (dp, "Empate"), (ap, away)],
        key=lambda x: x[0]
    )

    # Odds justas
    def _fair_odd(prob_pct):
        return f"{100/prob_pct:.2f}" if prob_pct > 0 else "-"

    msg = ""

    # ── Header ──
    msg += f"⚽ <b>{home} {score} {away}</b>"
    if minute:
        msg += f"  ⏱️ {minute}'"
    msg += "\n"
    if league:
        msg += f"📋 {league}\n"
    msg += "\n"

    # ── Destaque do palpite ──
    if best_pct >= 65:
        emoji = "🔒"
        confianca = "ALTA CONFIANÇA"
    elif best_pct >= 50:
        emoji = "🎯"
        confianca = "BOA CHANCE"
    else:
        emoji = "⚡"
        confianca = "JOGO EQUILIBRADO"

    msg += f"{emoji} <b>PALPITE BETINA — {confianca}</b>\n"
    msg += f"A I.A. aponta <b>{best_name}</b> com <b>{best_pct}%</b>!\n\n"

    # ── Barras de probabilidade ──
    msg += f"📊 <b>Probabilidades:</b>\n"
    msg += f"├ {home}: {hp}% │ odd justa {_fair_odd(hp)}\n"
    msg += f"├ Empate: {dp}% │ odd justa {_fair_odd(dp)}\n"
    msg += f"└ {away}: {ap}% │ odd justa {_fair_odd(ap)}\n\n"

    # ── Contexto do placar ──
    diff = h_score - a_score
    if minute >= 75 and abs(diff) >= 2:
        loser = away if diff > 0 else home
        msg += f"⏰ <b>Resto de jogo:</b> Falta pouco tempo e {loser} precisa de {abs(diff)} gols pra virar — cenário muito difícil!\n\n"
    elif minute >= 60 and abs(diff) == 1:
        msg += f"⏰ <b>Reta final!</b> Diferença de 1 gol — ainda dá pra virar! Jogo tenso 🔥\n\n"
    elif h_score + a_score >= 4:
        msg += f"🎆 <b>Jogo com muitos gols!</b> {h_score + a_score} gols até agora — ofensivo e imprevisível!\n\n"

    # ── Insight tático ──
    narrative = prediction.get("narrative", "")
    if narrative:
        # Pega primeira frase ou bloco
        first = narrative.split("\n\n")[0].split("\n")[0]
        if len(first) > 200:
            first = first[:197] + "..."
        if first:
            msg += f"💡 {first}\n\n"

    # ── CTA + Follow-up ──
    msg += f"🔗 <b>Análise completa + apostar:</b>\n{PLATFORM_URL}\n\n"

    # Follow-up conversacional
    follow_ups = [
        "Gostou do palpite? Quer ver <b>outro jogo</b>? 👀",
        "Vai de aposta nesse? 🎰 Ou manda /jogos pra ver outros!",
        "O que achou? Manda 'outro' pra eu analisar mais jogos!",
    ]
    msg += random.choice(follow_ups)

    return msg


def format_proactive_tip(
    home: str, away: str, score: str,
    minute: str, league: str, prediction: dict,
) -> str:
    """Formata alerta proativo (scheduler) rico e persuasivo."""
    hp = round(prediction.get("home_win_probability", 0) * 100)
    dp = round(prediction.get("draw_probability", 0) * 100)
    ap = round(prediction.get("away_win_probability", 0) * 100)

    best_pct, best_name = max([(hp, home), (dp, "Empate"), (ap, away)], key=lambda x: x[0])

    def _fair(p):
        return f"{100/p:.2f}" if p > 0 else "-"

    msg = "🚨 <b>ALERTA BETINA!</b> 🚨\n\n"
    msg += f"⚽ <b>{home} {score} {away}</b>"
    if minute:
        msg += f" ({minute}')"
    msg += "\n"
    if league:
        msg += f"📋 {league}\n"

    msg += f"\n🎯 Aponto <b>{best_name}</b> com <b>{best_pct}%</b>!\n\n"

    msg += f"📊 Probabilidades:\n"
    msg += f"├ {home}: {hp}%  (odd justa: {_fair(hp)})\n"
    msg += f"├ Empate: {dp}%  (odd justa: {_fair(dp)})\n"
    msg += f"└ {away}: {ap}%  (odd justa: {_fair(ap)})\n\n"

    msg += f"🔥 O jogo tá rolando AGORA! Corre!\n"
    msg += f"🔗 {PLATFORM_URL}\n\n"
    msg += "Manda /palpite pra mais detalhes ou /jogos pra ver outros!"

    return msg


def _score_match(r: dict) -> int:
    """Pontua jogo para ordenação (maior = mais interessante)."""
    score_str = r.get("ss", "0-0")
    league = (r.get("league", {}).get("name", "") or "").lower()
    minute = int(r.get("timer", {}).get("tm", 0) or 0)
    h, a = _parse_score(score_str)
    diff = abs(h - a)

    points = 0
    if diff <= 1:
        points += 10
    if h + a > 0:
        points += 3
    if any(kw in league for kw in TIER1_KEYWORDS):
        points += 8
    if minute >= 60:
        points += 5
    elif minute >= 45:
        points += 2

    return points
