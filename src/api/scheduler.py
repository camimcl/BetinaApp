"""
src/api/scheduler.py

Scheduler de envio proativo de palpites via Telegram.

- Verifica jogos ao vivo a cada 30 minutos
- Seleciona os mais "quentes" (placar apertado + liga tier-1)
- Envia no máximo 3 alertas por dia para chats registrados
- Roda predição real do modelo em cada jogo selecionado
"""

import os
import random
from datetime import datetime

from loguru import logger

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler não instalado: pip install apscheduler")

_scheduler = None


def start_proactive_scheduler():
    """Inicia o scheduler de envio proativo. Chamar no startup do FastAPI."""
    global _scheduler

    if not SCHEDULER_AVAILABLE:
        logger.warning("Scheduler não disponível — APScheduler não instalado.")
        return

    from src.api.telegram import is_configured
    if not is_configured():
        logger.warning("Scheduler não iniciado — TELEGRAM_BOT_TOKEN não configurado.")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _proactive_check,
        "interval",
        minutes=30,
        id="betina_proactive",
        name="Betina - Alerta Proativo Telegram",
        max_instances=1,
        next_run_time=datetime.now(),
    )
    _scheduler.start()
    logger.success("📲 Scheduler proativo iniciado (verifica a cada 30 min, máx 3 alertas/dia)")


def stop_scheduler():
    """Para o scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler parado.")


async def _proactive_check():
    """
    Job executado pelo scheduler:
    1. Verifica se pode enviar (< 3 alertas no dia)
    2. Busca jogos ao vivo
    3. Filtra os mais quentes
    4. Roda predição
    5. Envia para todos os chats registrados
    """
    from src.api.telegram import (
        can_send_today,
        get_registered_chats,
        get_daily_sends_count,
        send_message,
        format_proactive_tip,
        _pick_hottest_match,
        _increment_daily_counter,
    )

    chats = get_registered_chats()
    if not chats:
        logger.debug("Nenhum chat registrado — pular envio proativo.")
        return

    if not can_send_today():
        logger.debug(f"Limite diário atingido ({get_daily_sends_count()}/3) — pular.")
        return

    BETSAPI_TOKEN = os.getenv("BETSAPI_TOKEN", "")
    BETSAPI_BASE = "https://api.betsapi.com/v1"

    if not BETSAPI_TOKEN:
        logger.debug("BETSAPI_TOKEN não configurado — scheduler não pode buscar jogos.")
        return

    # 1. Busca jogos ao vivo
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BETSAPI_BASE}/events/inplay",
                params={"token": BETSAPI_TOKEN, "sport_id": 1}
            )
        data = resp.json()
        results = data.get("results", [])
    except Exception as e:
        logger.error(f"Scheduler: erro ao buscar jogos ao vivo: {e}")
        return

    if not results:
        logger.debug("Scheduler: nenhum jogo ao vivo encontrado.")
        return

    # 2. Seleciona o jogo mais quente
    best = _pick_hottest_match(results)
    if not best:
        logger.debug("Scheduler: nenhum jogo atingiu critério de 'quente'.")
        return

    home = best.get("home", {}).get("name", "Time A")
    away = best.get("away", {}).get("name", "Time B")
    score = best.get("ss", "0-0")
    minute = str(best.get("timer", {}).get("tm", "?"))
    league = best.get("league", {}).get("name", "")

    # Verifica qualidade mínima
    try:
        parts = score.split("-")
        diff = abs(int(parts[0]) - int(parts[1]))
    except (ValueError, IndexError):
        diff = 0

    min_val = int(minute) if minute.isdigit() else 0

    tier1_keywords = [
        "premier", "la liga", "serie a", "bundesliga", "ligue 1",
        "champions", "libertadores", "brasileir", "copa do mundo",
    ]
    league_lower = league.lower()
    is_tier1 = any(kw in league_lower for kw in tier1_keywords)

    if diff > 1 and not is_tier1:
        logger.debug(f"Scheduler: {home} vs {away} ({score}) não é quente o suficiente.")
        return

    if min_val < 30 and not is_tier1:
        logger.debug(f"Scheduler: {home} vs {away} muito cedo ({minute}') para alertar.")
        return

    # 3. Roda predição real
    try:
        score_parts = score.split("-")
        h_score = int(score_parts[0]) if score_parts else 0
        a_score = int(score_parts[1]) if len(score_parts) > 1 else 0
    except (ValueError, IndexError):
        h_score, a_score = 0, 0

    from src.api.telegram import _build_match_features
    match_data = _build_match_features(h_score, a_score)

    try:
        from src.models.predictor import predict_match
        prediction = predict_match(
            match_data,
            home_team_name=home,
            away_team_name=away,
            home_score=h_score,
            away_score=a_score,
            minute=min_val,
        )
    except Exception as e:
        logger.error(f"Scheduler: erro na predição de {home} vs {away}: {e}")
        return

    # 4. Formata mensagem
    message = format_proactive_tip(
        home=home, away=away, score=score,
        minute=minute, league=league, prediction=prediction
    )

    # 5. Envia para todos os registrados
    sent_count = 0
    for chat_id in chats:
        result = await send_message(chat_id, message)
        if result["status"] == "sent":
            sent_count += 1

    if sent_count > 0:
        _increment_daily_counter()
        logger.success(
            f"📲 Alerta proativo enviado! {home} vs {away} ({score}) → "
            f"{sent_count}/{len(chats)} chats (envio {get_daily_sends_count()}/3 do dia)"
        )
