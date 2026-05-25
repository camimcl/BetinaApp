"""
src/api/gemini_client.py

Cliente Gemini para narrativas dinâmicas e chat conversacional.
Usa o novo SDK: google-genai (pip install google-genai)
Modelo: gemini-2.5-flash (free tier)

Funcionalidades:
  - generate_match_narrative(): analisa um jogo e gera texto rico variado
  - chat_with_betina(): sessão multi-turn com histórico por session_id
  - Fallback automático se GEMINI_API_KEY não estiver configurada

Variáveis de ambiente necessárias:
    GEMINI_API_KEY=<sua_chave_do_google_ai_studio>
"""

import os
import random
import time
import hashlib
from typing import Optional

from loguru import logger

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-genai não instalado. Execute: pip install google-genai")

# ── Configuração ──────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# gemini-2.5-flash: modelo mais recente disponível no free tier
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_client: Optional[object] = None


# ── Rate Limiter Global ──────────────────────────────────────────────────────
# Free tier gemini-2.5-flash: ~10 req/min
# Mantemos margem de segurança: max 6 req/min

_rate_limit_timestamps: list = []  # timestamps das últimas chamadas
_MAX_REQUESTS_PER_MINUTE = 6
_cooldown_until: float = 0.0       # timestamp até quando pausar (após 429)


def _can_call_api() -> bool:
    """Verifica se pode fazer uma chamada respeitando rate limit e cooldown."""
    global _cooldown_until

    now = time.time()

    # Cooldown ativo após um 429
    if now < _cooldown_until:
        remaining = round(_cooldown_until - now)
        logger.debug(f"Gemini em cooldown — {remaining}s restantes")
        return False

    # Remove timestamps mais velhos que 60s
    cutoff = now - 60
    while _rate_limit_timestamps and _rate_limit_timestamps[0] < cutoff:
        _rate_limit_timestamps.pop(0)

    # Verifica se atingiu o limite
    if len(_rate_limit_timestamps) >= _MAX_REQUESTS_PER_MINUTE:
        logger.debug(f"Rate limit atingido ({len(_rate_limit_timestamps)}/{_MAX_REQUESTS_PER_MINUTE} req/min)")
        return False

    return True


def _register_call():
    """Registra uma chamada feita."""
    _rate_limit_timestamps.append(time.time())


def _activate_cooldown(seconds: int = 30):
    """Ativa cooldown após erro 429."""
    global _cooldown_until
    _cooldown_until = time.time() + seconds
    logger.warning(f"Gemini: cooldown ativado por {seconds}s após 429")


# ── Cache de Narrativas ──────────────────────────────────────────────────────
# Evita chamar Gemini para o mesmo jogo com os mesmos dados
_narrative_cache: dict = {}  # {hash: {"text": str, "time": float}}
_CACHE_TTL = 300  # 5 minutos


def _cache_key(home: str, away: str, home_pct: float, away_pct: float) -> str:
    """Gera chave de cache baseada nos dados do jogo."""
    raw = f"{home}:{away}:{round(home_pct)}:{round(away_pct)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached_narrative(key: str) -> Optional[str]:
    """Busca narrativa no cache se ainda válida."""
    entry = _narrative_cache.get(key)
    if entry and (time.time() - entry["time"]) < _CACHE_TTL:
        logger.debug(f"Narrativa servida do cache (key={key[:8]})")
        return entry["text"]
    return None


def _set_cached_narrative(key: str, text: str):
    """Salva narrativa no cache."""
    _narrative_cache[key] = {"text": text, "time": time.time()}
    # Limpa entradas antigas (max 50)
    if len(_narrative_cache) > 50:
        oldest = sorted(_narrative_cache.items(), key=lambda x: x[1]["time"])[:10]
        for k, _ in oldest:
            _narrative_cache.pop(k, None)


def _get_client():
    """Retorna (ou cria) o cliente Gemini singleton."""
    global _client
    if _client is not None:
        return _client
    if not GEMINI_AVAILABLE:
        return None
    if not GEMINI_API_KEY:
        logger.debug("GEMINI_API_KEY não configurada — usando fallback local")
        return None
    _client = genai.Client(api_key=GEMINI_API_KEY)
    logger.debug("Cliente Gemini (google-genai) inicializado.")
    return _client


def is_available() -> bool:
    """Retorna True se o Gemini está configurado e disponível."""
    return GEMINI_AVAILABLE and bool(GEMINI_API_KEY)


def _extract_text(response) -> str:
    """
    Extrai texto de uma resposta Gemini de forma robusta.
    Modelos 'thinking' (ex: gemini-2.5-flash) podem retornar
    response.text=None quando há thinking parts. Esta função
    itera pelas parts e extrai apenas o texto real.
    """
    # Caminho rápido: response.text existe
    try:
        if response.text is not None:
            return response.text.strip()
    except (AttributeError, ValueError):
        pass

    # Caminho robusto: extrair de candidates[0].content.parts
    try:
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                texts = []
                for part in candidate.content.parts:
                    # Ignora thinking parts (part.thought == True)
                    if hasattr(part, 'thought') and part.thought:
                        continue
                    if part.text:
                        texts.append(part.text)
                if texts:
                    return "\n".join(texts).strip()
    except (AttributeError, IndexError):
        pass

    return ""


# ── Prompt System ─────────────────────────────────────────────────────────────

BETINA_SYSTEM_PROMPT = """Você é a Elli, uma analista esportiva de elite especializada em leitura tática de partidas de futebol — com domínio total de dados e estatísticas preditivas.

Seu estilo de comunicação:
- Tom: autoridade analítica + envolvimento conversacional. Como um comentarista técnico experiente falando diretamente com o usuário.
- Formatação: Sempre organize sua resposta em blocos bem separados com títulos em **negrito** e emojis temáticos. Pule uma linha entre cada bloco. Não use listas contínuas sem espaçamento.
- Linguagem: Português brasileiro natural. Nomes de times sempre em negrito.
- Proibido usar: "xG", "SHAP", "features", "modelo", "mandante", "visitante", "odds ao vivo disponíveis".
- Substitua termos técnicos por: "oportunidades criadas", "eficiência ofensiva", "domínio territorial", "pressão constante", "qualidade das finalizações".
- Regra absolutamente inegociável: TODAS as porcentagens devem ser números inteiros, sem casas decimais (ex: **52%**, NUNCA 52.1% ou 52.10%).
- Use emojis de modo estratégico para demarcar seções (🎯, 📊, ⚔️, 🛡️, 💡, ⚽, 🔥).
"""


# ── Narrativa de Partida ──────────────────────────────────────────────────────

def generate_match_narrative(
    home_name: str,
    away_name: str,
    home_pct: float,
    draw_pct: float,
    away_pct: float,
    match_stats: dict,
    factors: list,
) -> Optional[str]:
    """
    Gera narrativa rica para análise de partida usando Gemini.
    Retorna None se Gemini não disponível (usar fallback).

    Otimizações:
    - Cache: reutiliza narrativa para mesmos times/probabilidades (TTL 5min)
    - Rate limiter: max 8 req/min para respeitar free tier
    - Cooldown: pausa automática de 30s após erro 429
    """
    client = _get_client()
    if client is None:
        return None

    # 1. Verifica cache primeiro (sem gastar req)
    ck = _cache_key(home_name, away_name, home_pct, away_pct)
    cached = _get_cached_narrative(ck)
    if cached:
        return cached

    # 2. Rate limit check
    if not _can_call_api():
        logger.debug("Narrativa pulada — rate limit ou cooldown ativo")
        return None

    # Monta contexto de estatísticas humanizadas
    hs  = match_stats.get("home_shots", 0)
    aws = match_stats.get("away_shots", 0)
    hso = match_stats.get("home_shots_ot", 0)
    aso = match_stats.get("away_shots_ot", 0)
    hpa = match_stats.get("home_pass_acc", 0)
    apa = match_stats.get("away_pass_acc", 0)
    pr  = match_stats.get("pressure_ratio", 1.0)

    stats_lines = []
    if hs or aws:
        stats_lines.append(
            f"Finalizações: {home_name} criou {hs} chutes ({hso} no alvo) | "
            f"{away_name} criou {aws} chutes ({aso} no alvo)."
        )
    if hpa or apa:
        stats_lines.append(
            f"Precisão de passe: {home_name} com {hpa*100:.0f}% | {away_name} com {apa*100:.0f}%."
        )
    if pr > 1.15:
        stats_lines.append(f"Controle territorial: {home_name} pressiona com mais intensidade.")
    elif pr < 0.85:
        stats_lines.append(f"Controle territorial: {away_name} dita o ritmo apesar de jogar fora.")

    factor_humanized = _humanize_factors(factors, home_name, away_name, match_stats)
    if factor_humanized:
        stats_lines.append(f"Fator decisivo: {factor_humanized}.")

    stats_text = "\n".join(stats_lines) if stats_lines else "Dados iniciais limitados — análise baseada no contexto geral da partida."

    # Identifica favorito
    ranked = sorted(
        [(home_pct, home_name), (draw_pct, "Empate"), (away_pct, away_name)],
        key=lambda x: x[0], reverse=True
    )
    fav_pct, fav_name = ranked[0]

    prompt = f"""Gere uma análise curta desta partida (máx 4 blocos, cada um com 1-2 frases):

{home_name} vs {away_name}
Probabilidades: {home_name} {home_pct:.0f}% | Empate {draw_pct:.0f}% | {away_name} {away_pct:.0f}%
Estatísticas: {stats_text}

Estrutura:
1. 🎯 Cenário favorito (1 frase com % e nome do favorito)
2. 📊 Por que esse favoritismo? (2 frases)
3. ⚔️ Dinâmica do jogo (1 frase)
4. 💡 Radar Betina (1 observação final)

Regras: porcentagens inteiras, sem jargão técnico, nomes em **negrito**.
"""

    try:
        _register_call()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=BETINA_SYSTEM_PROMPT,
                temperature=0.75,
                max_output_tokens=400,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = _extract_text(response)
        if not text:
            logger.warning("Gemini retornou resposta vazia para narrativa")
            return None
        _set_cached_narrative(ck, text)
        return text
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            _activate_cooldown(30)
        logger.error(f"Gemini generate_match_narrative falhou: {e}")
        return None


def _humanize_factors(factors: list, home_name: str, away_name: str, stats: dict) -> str:
    """Converte fatores SHAP em frase explicativa com dados reais."""
    if not factors:
        return ""

    top = factors[0]
    feat = top.get("feature", "")
    direction = top.get("direction", "aumenta")
    favored = home_name if direction == "aumenta" else away_name

    if "shots_ot" in feat:
        val = stats.get("home_shots_ot" if "home" in feat else "away_shots_ot", 0)
        team = home_name if "home" in feat else away_name
        return f"qualidade das finalizações no alvo — {team} com {val} chutes certeiros (favorece {favored})"
    if "xg" in feat or "shots" in feat:
        team = home_name if "home" in feat else away_name
        return f"volume ofensivo de {team} é o principal termômetro desta análise"
    if "pass_acc" in feat:
        val = stats.get("home_pass_acc" if "home" in feat else "away_pass_acc", 0)
        team = home_name if "home" in feat else away_name
        return f"eficiência de circulação de bola de {team} ({val*100:.0f}%) pressiona a decisão do jogo"
    if "pressure" in feat:
        return f"domínio territorial é o principal diferencial neste duelo"

    label = top.get("label", feat.replace("_", " "))
    return f"{label.capitalize()} inclina a balança para {favored}"


# ── Simulação E Se ────────────────────────────────────────────────────────────

def generate_simulation_narrative(
    prediction_type: str,
    description: str,
    changes: dict,
    pct_change: float,
    impact_pct_change: float = None,
) -> str:
    """Gera uma narrativa dupla em português claro para um cenário hipotético."""
    target_desc = "gol" if prediction_type == "shot" else "cartão" if prediction_type == "foul" else "vitória da equipe da casa"
    
    # Humanizar chaves das changes
    human_changes = []
    for k, v in changes.items():
        if k in ("xg", "home_xg", "away_xg"): name = "Qualidade da Oportunidade (xG)"
        elif k == "distance_to_goal": name = "Distância do Arremate"
        elif k == "under_pressure": name = "Nível de Marcação/Pressão"
        elif k == "angle_to_goal": name = "Ângulo de Visão"
        elif k in ("home_score", "away_score"): name = "Diferença no Placar"
        elif "shots" in k: name = "Volume de Finalizações"
        elif "pass_acc" in k: name = "Precisão e Posse de Bola"
        elif "pressure_ratio" in k: name = "Domínio Territorial"
        elif k == "is_home_team": name = "Time Base (Mandante/Visitante)"
        elif k == "open_goal": name = "Arremate Sem Goleiro"
        elif k == "in_danger_zone": name = "Local da Ocorrência"
        elif k == "in_final_third": name = "Proximidade do Gol"
        else: name = k.replace("_", " ").title()
        human_changes.append(f"{name} ({v})")

    changes_text = "\n".join(human_changes)
    changes_inline = " e ".join([c.split("(")[0].strip() for c in human_changes])

    client = _get_client()

    # ── Fallback rico (sem Gemini) ────────────────────────────────────────────
    def _rich_fallback() -> str:
        import random
        abs_pct = abs(pct_change)
        positive = pct_change > 0
        is_shot = prediction_type == "shot"
        is_foul = prediction_type == "foul"
        is_match = prediction_type == "match"

        # Nível de impacto
        if abs_pct >= 20:
            impacto = "expressivo"
            emoji_imp = "🔥"
        elif abs_pct >= 10:
            impacto = "significativo"
            emoji_imp = "⚡"
        elif abs_pct >= 5:
            impacto = "moderado"
            emoji_imp = "📊"
        else:
            impacto = "sutil"
            emoji_imp = "💡"

        # Frases de abertura por tipo
        if is_shot:
            if positive:
                abertura_opts = [
                    f"🎯 **Sua Análise Tática, na Lata!**\n\nCom a alteração em **{changes_inline}**, a simulação aponta um aumento {impacto} de **{abs_pct}%** na probabilidade de gol. Esse cenário coloca o atacante em vantagem clara sobre a defesa adversária.",
                    f"🎯 **Cenário Favorável Detectado!**\n\nAjustar **{changes_inline}** eleva a chance de conversão em **{abs_pct}%**. Um impacto {impacto} que comprova como detalhes táticos transformam a qualidade de uma finalização.",
                    f"⚽ **Análise do Chute**\n\nA simulação indica que modificar **{changes_inline}** melhora consideravelmente a eficiência do lance, com ganho de **{abs_pct}%** na probabilidade de gol. Posicionamento e pressão fazem toda a diferença.",
                ]
            else:
                abertura_opts = [
                    f"🛡️ **Cenário Defensivo**\n\nCom essas condições — **{changes_inline}** — a probabilidade de gol cai **{abs_pct}%**. A marcação intensa dificulta a conclusão e reduz consideravelmente o perigo da jogada.",
                    f"📊 **Análise do Chute**\n\nAlterando **{changes_inline}**, a simulação aponta redução de **{abs_pct}%** na chance de gol. Esse cenário mostra como a pressão defensiva muda completamente o panorama da finalização.",
                ]
        elif is_foul:
            if positive:
                abertura_opts = [
                    f"🟨 **Risco Elevado Identificado!**\n\nCom **{changes_inline}** nessas condições, a probabilidade de cartão sobe **{abs_pct}%**. A localização e a intensidade da falta são determinantes para a decisão arbitral.",
                    f"⚠️ **Análise da Falta**\n\nA simulação indica que **{changes_inline}** eleva o risco de cartão em **{abs_pct}%**. Árbitros tendem a ser mais rigorosos em situações de alta pressão e proximidade da área.",
                ]
            else:
                abertura_opts = [
                    f"✅ **Risco Controlado**\n\nNessas condições — **{changes_inline}** — a probabilidade de cartão cai **{abs_pct}%**. A posição da falta e o contexto do lance reduzem a percepção de perigo para o árbitro.",
                    f"🟩 **Análise da Falta**\n\nModificando **{changes_inline}**, o risco de punição diminui **{abs_pct}%**. Um ajuste {impacto} que mostra como o posicionamento influencia diretamente as decisões do árbitro.",
                ]
        else:  # match
            if positive:
                abertura_opts = [
                    f"📈 **Cenário de Domínio**\n\nAjustar **{changes_inline}** projeta um aumento de **{abs_pct}%** nas chances de vitória. O volume e a qualidade das ações ofensivas são os grandes motores desse favoritismo.",
                    f"🏆 **Projeção Tática**\n\nCom **{changes_inline}** nesse patamar, a simulação aponta ganho de **{abs_pct}%** na probabilidade de vitória. Um indicativo {impacto} de que esse cenário favorece claramente uma das equipes.",
                ]
            else:
                abertura_opts = [
                    f"📉 **Cenário Adverso**\n\nCom **{changes_inline}** nessas condições, a probabilidade de vitória cai **{abs_pct}%**. O adversário ganha vantagem territorial e de criação de oportunidades.",
                    f"⚖️ **Projeção Tática**\n\nModificando **{changes_inline}**, a simulação registra queda de **{abs_pct}%** nas chances de vitória. Isso evidencia como a posse e o volume ofensivo definem o favorito da partida.",
                ]

        linha_abertura = random.choice(abertura_opts)

        # Linha de impacto na vitória
        linha_impacto = ""
        if impact_pct_change is not None and is_shot or impact_pct_change is not None and is_foul:
            abs_imp = abs(impact_pct_change)
            if impact_pct_change > 0:
                linha_impacto = (
                    f"\n\n{emoji_imp} **Impacto na Vitória**\n\n"
                    f"Se esse lance se concretizar em jogo, o time ganha um impulso de **{abs_imp}%** nas chances de sair com os três pontos. "
                    + random.choice([
                        "Um divisor de águas que pode redefinir o equilíbrio da partida.",
                        "Exatamente o tipo de situação que muda o estado psicológico das duas equipes.",
                        "Esse tipo de jogada transforma cenários incertos em vantagens concretas no placar.",
                    ])
                )
            else:
                linha_impacto = (
                    f"\n\n📉 **Impacto na Vitória**\n\n"
                    f"A concretização desse lance, nesse cenário, reduziria as chances de vitória do time em **{abs_imp}%**. "
                    + random.choice([
                        "Um sinal de alerta tático que não pode ser ignorado.",
                        "Resultado que reforça a importância de criar situações mais favoráveis antes de finalizar.",
                        "Isso demonstra como as condições do lance definem o impacto real no resultado final.",
                    ])
                )

        # Reflexão final
        reflexao_opts = [
            f"\n\n💡 **Reflexão Estratégica**\n\nEssa simulação reforça como pequenos ajustes táticos geram consequências {impacto}s no resultado. A Elli AI continua monitorando os dados em tempo real para te dar as melhores análises.",
            f"\n\n💡 **Leitura Tática**\n\nOs números confirmam: detalhes como **{changes_inline}** não são triviais — eles mudam completamente o panorama do lance e do jogo. Fique atento às próximas jogadas.",
        ]
        reflexao = random.choice(reflexao_opts)

        return linha_abertura + linha_impacto + reflexao

    if client is None or not _can_call_api():
        return _rich_fallback()

    prompt = f"""Atue como Elli, analista de dados esportivos.
Acabamos de rodar uma simulação hipotética "E SE".

- Descrição do cenário escolhido pelo usuário: {description}
- O que o usuário alterou nos dados do jogo:
{changes_text}

- A Conclusão Matemática: a probabilidade do lance ({target_desc}) ocorrer teve um delta de {pct_change}% (pontos percentuais).
"""
    if impact_pct_change is not None:
        prompt += f"- O Impacto Real: se esse {target_desc} se concretizar na partida, a probabilidade do time VENCER vai ter um impacto direto de {impact_pct_change}%!\n"

    prompt += f"""
Monte uma análise de 2 a 3 frases. 
Sem asteriscos e adotando tom profissional de análise estatística. {"Destaque tanto a probabilidade natural do lance ocorrer, quanto o aumento ou redução do percentual de vitória caso o lance aconteça no placar real." if impact_pct_change is not None else "Explique de forma objetiva por que essa alteração muda a estatística inicial."} Analise matematicamente o impacto gerado!
"""

    try:
        _register_call()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=BETINA_SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=250,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = _extract_text(response)
        return text.replace("*", "") if text else _rich_fallback()
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            _activate_cooldown(30)
        logger.error(f"Gemini generate_simulation_narrative falhou: {e}")
        return _rich_fallback()


# ── Sessão de Chat Multi-Turn ─────────────────────────────────────────────────

# Armazena histórico por session_id: lista de types.Content
_session_histories: dict = {}


def chat_with_betina(
    session_id: str,
    user_message: str,
    match_context: Optional[dict] = None,
) -> str:
    """
    Envia mensagem ao Gemini com histórico da sessão (multi-turn manual).

    Args:
        session_id: identificador único da sessão do usuário
        user_message: mensagem enviada pelo usuário
        match_context: contexto opcional do jogo selecionado

    Returns:
        Resposta da Betina (str). Usa fallback se Gemini indisponível.
    """
    client = _get_client()
    if client is None or not _can_call_api():
        return _fallback_chat_response(user_message, match_context)

    # Recupera ou cria histórico
    history = _session_histories.setdefault(session_id, [])

    # Injeta contexto do jogo na mensagem do usuário se disponível
    full_message = user_message
    if match_context:
        ctx = _build_match_context_text(match_context)
        full_message = f"[Contexto do jogo ativo: {ctx}]\n\nUsuário: {user_message}"

    # Adiciona mensagem do usuário ao histórico
    history.append(
        genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=full_message)])
    )

    try:
        _register_call()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=history,
            config=genai_types.GenerateContentConfig(
                system_instruction=BETINA_SYSTEM_PROMPT,
                temperature=0.8,
                max_output_tokens=350,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        reply = _extract_text(response)
        if not reply:
            logger.warning(f"Gemini retornou vazio (session={session_id})")
            _session_histories.pop(session_id, None)
            return _fallback_chat_response(user_message, match_context)

        # Adiciona resposta do modelo ao histórico para multi-turn
        history.append(
            genai_types.Content(role="model", parts=[genai_types.Part.from_text(text=reply)])
        )

        # Limita histórico a últimas 20 mensagens para não explodir tokens
        if len(history) > 20:
            _session_histories[session_id] = history[-20:]

        return reply
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            _activate_cooldown(30)
        logger.error(f"Gemini chat falhou (session={session_id}): {e}")
        _session_histories.pop(session_id, None)
        return _fallback_chat_response(user_message, match_context)


def clear_session(session_id: str):
    """Remove histórico da sessão do cache."""
    _session_histories.pop(session_id, None)


def _build_match_context_text(ctx: dict) -> str:
    """Formata o contexto do jogo para injetar no prompt."""
    home = ctx.get("home_team", "")
    away = ctx.get("away_team", "")
    score = ctx.get("score", "0-0")
    minute = ctx.get("time", "")
    league = ctx.get("league", "")

    parts = [f"{home} {score} {away}"]
    if minute:
        parts.append(f"{minute}' jogados")
    if league:
        parts.append(league)

    pred = ctx.get("prediction", {})
    if pred:
        hp = round(pred.get("home_win_probability", 0) * 100)
        dp = round(pred.get("draw_probability", 0) * 100)
        ap = round(pred.get("away_win_probability", 0) * 100)
        parts.append(
            f"Probabilidades: {home} {hp}% | Empate {dp}% | {away} {ap}%"
        )

    return " | ".join(parts)


# ── Fallback Local ────────────────────────────────────────────────────────────

def _fallback_chat_response(user_message: str, match_context: Optional[dict] = None) -> str:
    """Resposta de fallback quando Gemini não está disponível."""
    lower = user_message.lower()
    home = match_context.get("home_team", "") if match_context else ""
    away = match_context.get("away_team", "") if match_context else ""
    game_str = f"**{home}** vs **{away}**" if home else "o jogo selecionado"

    if any(w in lower for w in ["palpite", "chance", "probabilidade", "resultado", "análise"]):
        if match_context and match_context.get("prediction"):
            pred = match_context["prediction"]
            hp = round(pred.get("home_win_probability", 0) * 100)
            dp = round(pred.get("draw_probability", 0) * 100)
            ap = round(pred.get("away_win_probability", 0) * 100)
            dominant = max([(hp, home), (dp, "Empate"), (ap, away)], key=lambda x: x[0])
            return (
                f"🎯 Para {game_str}, o modelo aponta:\n\n"
                f"⚽ **{home}**: {hp}%\n"
                f"⚖️ **Empate**: {dp}%\n"
                f"⚽ **{away}**: {ap}%\n\n"
                f"💡 **Radar Elli**: {dominant[1]} aparece como cenário favorito com {dominant[0]}% de probabilidade."
            )

    if any(w in lower for w in ["aposta", "odd", "valor", "bet"]):
        return (
            "💡 Compare a probabilidade calculada pelo modelo com a odd que você encontrar.\n\n"
            "A fórmula é simples: se nossa **% de chance > 1 ÷ odd**, existe valor potencial na aposta. 🔥"
        )

    if any(w in lower for w in ["simul", "e se", "what if"]):
        return "🔮 Use a aba **Simulação** para testar cenários hipotéticos — como seria o jogo se uma variável chave mudasse!"

    if any(w in lower for w in ["oi", "olá", "ola", "tudo", "bem"]):
        return (
            f"Olá! 👋 Sou a **Elli AI**, analista de partidas com IA.\n\n"
            f"{'Estou analisando ' + game_str + ' agora. Me pergunte o que quiser sobre a partida!' if home else 'Selecione um jogo ao vivo na barra lateral e vou te dar uma análise completa! ⚽'}"
        )

    return random.choice([
        "📊 Selecione um jogo ao vivo na barra lateral para eu montar uma análise completa com dados reais!",
        "⚽ Para uma leitura precisa, preciso de um jogo ativo. Escolha um na lista lateral!",
        "💡 Posso te ajudar com análises de jogo, leitura de probabilidades e simulações. O que você quer saber?",
    ])


# ── Telegram — Prompt e Chat Específicos ──────────────────────────────────────

BETINA_WHATSAPP_PROMPT = """Você é a Elli, assistente de apostas esportivas no Telegram. Seu OBJETIVO PRINCIPAL é engajar o usuário e levá-lo a acessar a plataforma de apostas.

Seu tom no Telegram:
- DIRETO e PERSUASIVO — como uma amiga que manja muito de futebol e está empolgada com um jogo.
- Use linguagem informal, emojis frequentes (🔥⚽💰🎯📊) e frases curtas.
- SEMPRE finalize com uma pergunta ou call-to-action (CTA) para manter a conversa ativa.
- Quando apresentar um palpite, use urgência: "acontecendo AGORA", "corre que ainda dá tempo", "essa odd não vai durar".
- Use negrito com <b>texto</b> (HTML do Telegram). NÃO use asteriscos.
- Porcentagens SEMPRE inteiros (52%, nunca 52.1%).
- Nunca use termos técnicos (xG, SHAP, features). Fale "oportunidades de gol", "eficiência", "domínio de jogo".
- Se o usuário perguntar algo que você não sabe, redirecione para a plataforma.
"""

PLATFORM_URL = os.getenv("PLATFORM_URL", "http://localhost:5173")

# Sessões de chat separadas (por chat_id)
_whatsapp_sessions: dict = {}


def chat_with_betina_whatsapp(
    phone_number: str,
    user_message: str,
    match_context: Optional[dict] = None,
) -> str:
    """
    Chat com a Betina via WhatsApp — usa prompt persuasivo e sessão por telefone.
    """
    client = _get_client()
    if client is None or not _can_call_api():
        return _fallback_whatsapp_response(user_message, match_context)

    history = _whatsapp_sessions.setdefault(phone_number, [])

    full_message = user_message
    if match_context:
        ctx_parts = []
        home = match_context.get("home_team", "")
        away = match_context.get("away_team", "")
        if home:
            ctx_parts.append(f"Jogo: {home} vs {away}")
        score = match_context.get("score", "")
        if score:
            ctx_parts.append(f"Placar: {score}")
        pred = match_context.get("prediction", {})
        if pred:
            hp = round(pred.get("home_win_probability", 0) * 100)
            dp = round(pred.get("draw_probability", 0) * 100)
            ap = round(pred.get("away_win_probability", 0) * 100)
            ctx_parts.append(f"Análise: {home} {hp}% | Empate {dp}% | {away} {ap}%")
            fair_home = f"{1/pred['home_win_probability']:.2f}" if pred.get("home_win_probability", 0) > 0 else "-"
            fair_away = f"{1/pred['away_win_probability']:.2f}" if pred.get("away_win_probability", 0) > 0 else "-"
            ctx_parts.append(f"Odds justas: {home} {fair_home} | {away} {fair_away}")
        ctx_text = " | ".join(ctx_parts)
        full_message = f"[Contexto do jogo: {ctx_text}]\n\nMensagem do usuário: {user_message}"

    history.append(
        genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=full_message)])
    )

    try:
        _register_call()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=history,
            config=genai_types.GenerateContentConfig(
                system_instruction=BETINA_WHATSAPP_PROMPT,
                temperature=0.9,
                max_output_tokens=300,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        reply = _extract_text(response)
        if not reply:
            logger.warning(f"Gemini Telegram retornou vazio ({phone_number})")
            _whatsapp_sessions.pop(phone_number, None)
            return _fallback_whatsapp_response(user_message, match_context)

        history.append(
            genai_types.Content(role="model", parts=[genai_types.Part.from_text(text=reply)])
        )

        if len(history) > 16:
            _whatsapp_sessions[phone_number] = history[-16:]

        return reply
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            _activate_cooldown(30)
        logger.error(f"Gemini Telegram chat falhou ({phone_number}): {e}")
        _whatsapp_sessions.pop(phone_number, None)
        return _fallback_whatsapp_response(user_message, match_context)


def _fallback_whatsapp_response(user_message: str, match_context: Optional[dict] = None) -> str:
    """Fallback para WhatsApp quando Gemini não disponível."""
    lower = user_message.lower()
    platform = os.getenv("PLATFORM_URL", "http://localhost:5173")

    if match_context and match_context.get("prediction"):
        pred = match_context["prediction"]
        home = match_context.get("home_team", "Time A")
        away = match_context.get("away_team", "Time B")
        hp = round(pred.get("home_win_probability", 0) * 100)
        dp = round(pred.get("draw_probability", 0) * 100)
        ap = round(pred.get("away_win_probability", 0) * 100)
        best = max([(hp, home), (dp, "Empate"), (ap, away)], key=lambda x: x[0])
        return (
            f"⚽ *{home} vs {away}*\n\n"
            f"🎯 A I.A. aponta *{best[1]}* com *{best[0]}%* de chance!\n\n"
            f"📊 {home}: {hp}% | Empate: {dp}% | {away}: {ap}%\n\n"
            f"🔥 Quer apostar? Veja a análise completa:\n{platform}\n\n"
            f"O que acha desse palpite? 👀"
        )

    if any(w in lower for w in ["oi", "olá", "ola", "hi", "start"]):
        return (
            f"Fala! 👋 Sou a *Elli AI*, sua parceira de palpites esportivos!\n\n"
            f"🔥 Manda *jogo* e eu te mostro os jogos ao vivo com análise da I.A.\n"
            f"📊 Manda *palpite* pra receber dicas quentes!\n"
            f"🔔 Manda *alertas* pra receber notificações dos melhores jogos!\n\n"
            f"Ou acessa a plataforma completa: {platform}"
        )

    return (
        f"Não peguei bem 🤔 Tenta um desses:\n\n"
        f"⚽ *jogo* — Ver partidas ao vivo\n"
        f"📊 *palpite* — Receber análise\n"
        f"🔔 *alertas* — Ativar notificações\n"
        f"❌ *sair* — Parar notificações\n\n"
        f"Ou acessa: {platform}"
    )

