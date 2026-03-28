"""
src/api/main.py

API FastAPI do assistente de análise esportiva.

Rotas:
  GET  /health                     → status da API e modelos
  POST /predict/shot               → P(gol) dado um chute
  POST /predict/foul               → P(cartão) dada uma falta
  POST /predict/match              → P(resultado) dada uma partida
  POST /simulate                   → cenário "E SE?"
  GET  /live/matches               → partidas ao vivo via BetsAPI
  GET  /live/match/{event_id}      → detalhes de partida ao vivo

Uso:
    uvicorn src.api.main:app --reload --port 8000
"""

import os
from typing import Any, Dict, List, Optional

# CRÍTICO: load_dotenv DEVE rodar ANTES dos imports de módulos do projeto,
# pois eles lêem os.getenv() no topo do módulo durante a importação.
from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from src.models.predictor import (
    load_models,
    predict_foul,
    predict_match,
    predict_shot,
    simulate_what_if,
)
from src.api.telegram import (
    handle_incoming_message,
    is_configured as telegram_is_configured,
    send_message as send_telegram_message,
    register_chat,
    unregister_chat,
    get_registered_chats,
    get_daily_sends_count,
    format_proactive_tip,
)
from src.api.gemini_client import chat_with_betina, is_available as gemini_is_available
from src.api.scheduler import start_proactive_scheduler


BETSAPI_TOKEN = os.getenv("BETSAPI_TOKEN", "")
BETSAPI_BASE  = "https://api.betsapi.com/v1"

app = FastAPI(
    title="Sports Analysis Assistant API",
    description="Assistente de análise esportiva com XGBoost + SHAP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    logger.info("Carregando modelos...")
    try:
        load_models()
        logger.success("Modelos carregados com sucesso.")
    except FileNotFoundError as e:
        logger.warning(f"Modelos não encontrados — rode o treinamento primeiro: {e}")

    # Inicia scheduler de envio proativo Telegram
    try:
        start_proactive_scheduler()
    except Exception as e:
        logger.warning(f"Scheduler proativo não iniciou: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class ShotInput(BaseModel):
    distance_to_goal: float = Field(..., example=15.0, description="Distância ao gol em metros")
    angle_to_goal: float    = Field(..., example=30.0, description="Ângulo para o gol em graus")
    xg: float               = Field(..., example=0.12, description="xG do StatsBomb")
    technique: str          = Field("Normal", example="Normal")
    body_part: str          = Field("Right Foot", example="Right Foot")
    shot_type: str          = Field("Open Play", example="Open Play")
    first_time: int         = Field(0, example=0)
    open_goal: int          = Field(0, example=0)
    follows_dribble: int    = Field(0, example=0)
    under_pressure: int     = Field(0, example=1)
    minute: float           = Field(45.0, example=45.0)
    time_seconds: float     = Field(2700.0, example=2700.0)
    is_second_half: int     = Field(0, example=0)
    is_extra_time: int      = Field(0, example=0)
    score_diff: int         = Field(0, example=0)
    is_home_team: int       = Field(1, example=1)


class FoulInput(BaseModel):
    x: float                = Field(..., example=85.0)
    y: float                = Field(..., example=35.0)
    dist_to_center: float   = Field(25.0, example=25.0)
    in_danger_zone: int     = Field(0, example=0)
    in_final_third: int     = Field(1, example=1)
    foul_type: str          = Field("Regular", example="Regular")
    advantage: int          = Field(0, example=0)
    minute: float           = Field(78.0, example=78.0)
    time_seconds: float     = Field(4680.0, example=4680.0)
    is_second_half: int     = Field(1, example=1)
    is_last_10_min: int     = Field(0, example=0)
    under_pressure: int     = Field(1, example=1)
    score_diff: int         = Field(-1, example=-1)
    is_home_team: int       = Field(1, example=1)
    team_losing: int        = Field(1, example=1)


class MatchInput(BaseModel):
    home_team_name: str     = Field("Mandante", example="Flamengo")
    away_team_name: str     = Field("Visitante", example="Corinthians")
    home_score: int         = Field(0, example=0, description="Gols do mandante (ajuste live)")
    away_score: int         = Field(0, example=0, description="Gols do visitante (ajuste live)")
    minute: int             = Field(0, example=45, description="Minuto atual do jogo (ajuste live)")
    home_xg: float          = Field(..., example=1.8)
    away_xg: float          = Field(..., example=0.9)
    xg_diff: float          = Field(0.9, example=0.9)
    home_shots: int         = Field(12, example=12)
    away_shots: int         = Field(7, example=7)
    home_shots_ot: int      = Field(5, example=5)
    away_shots_ot: int      = Field(2, example=2)
    home_passes: int        = Field(450, example=450)
    away_passes: int        = Field(320, example=320)
    home_pass_acc: float    = Field(0.84, example=0.84)
    away_pass_acc: float    = Field(0.78, example=0.78)
    home_pressures: int     = Field(120, example=120)
    away_pressures: int     = Field(90, example=90)
    pressure_ratio: float   = Field(1.33, example=1.33)
    home_fouls: int         = Field(10, example=10)
    away_fouls: int         = Field(14, example=14)


class ChatInput(BaseModel):
    session_id: str         = Field(..., description="ID único da sessão do usuário")
    message: str            = Field(..., description="Mensagem do usuário")
    match_context: Optional[Dict[str, Any]] = Field(None, description="Contexto do jogo selecionado")


class SimulationInput(BaseModel):
    prediction_type: str    = Field(..., example="shot", description="'shot', 'foul' ou 'match'")
    base_data: Dict[str, Any]
    overrides: Dict[str, Any] = Field(..., description="Features a alterar no cenário hipotético")
    description: str        = Field("", example="E se o chute fosse mais perto do gol?")


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS DE PREDIÇÃO
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models_loaded": bool(os.path.exists("data/models/goal_model.pkl")),
        "betsapi_configured": bool(BETSAPI_TOKEN),
    }


@app.post("/predict/shot")
async def predict_shot_endpoint(shot: ShotInput):
    """
    Prediz a probabilidade de gol para um chute específico.
    Retorna probabilidade, fatores SHAP e narrativa em português.
    """
    try:
        result = predict_shot(shot.model_dump())
        return result
    except Exception as e:
        logger.error(f"Erro em /predict/shot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/foul")
async def predict_foul_endpoint(foul: FoulInput):
    """Prediz a probabilidade de cartão para uma falta."""
    try:
        result = predict_foul(foul.model_dump())
        return result
    except Exception as e:
        logger.error(f"Erro em /predict/foul: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/match")
async def predict_match_endpoint(match: MatchInput):
    """Prediz o resultado provável de uma partida com narrativa via Gemini."""
    try:
        data = match.model_dump()
        home_name = data.pop("home_team_name", "Mandante")
        away_name = data.pop("away_team_name", "Visitante")
        home_score = int(data.pop("home_score", 0))
        away_score = int(data.pop("away_score", 0))
        minute = int(data.pop("minute", 0))
        result = predict_match(
            data,
            home_team_name=home_name,
            away_team_name=away_name,
            home_score=home_score,
            away_score=away_score,
            minute=minute,
        )
        return result
    except Exception as e:
        logger.error(f"Erro em /predict/match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_endpoint(payload: ChatInput):
    """
    Chat conversacional com a Betina I.A. via Gemini.
    Mantém histórico multi-turn por session_id em memória.
    Aceita contexto do jogo selecionado para respostas contextualizadas.
    """
    try:
        response = chat_with_betina(
            session_id=payload.session_id,
            user_message=payload.message,
            match_context=payload.match_context,
        )
        return {
            "response": response,
            "session_id": payload.session_id,
            "gemini_active": gemini_is_available(),
        }
    except Exception as e:
        logger.error(f"Erro em /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulate")
async def simulate_endpoint(sim: SimulationInput):
    """
    Motor de simulação 'E SE?'.
    Recebe o cenário base e as alterações hipotéticas,
    retorna comparação entre os dois cenários com narrativa.
    """
    try:
        result = simulate_what_if(
            prediction_type=sim.prediction_type,
            base_data=sim.base_data,
            overrides=sim.overrides,
            description=sim.description,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro em /simulate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS BetsAPI — DADOS EM TEMPO REAL
# ══════════════════════════════════════════════════════════════════════════════

async def _betsapi_get(endpoint: str, params: dict = {}) -> dict:
    """Helper para chamadas à BetsAPI."""
    if not BETSAPI_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="BETSAPI_TOKEN não configurado. Adicione ao arquivo .env"
        )

    url = f"{BETSAPI_BASE}/{endpoint}"
    params = {"token": BETSAPI_TOKEN, **params}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"BetsAPI retornou {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    if data.get("success") != 1:
        raise HTTPException(status_code=502, detail=f"BetsAPI error: {data}")

    return data


@app.get("/live/matches")
async def get_live_matches(sport_id: int = Query(1, description="1=Soccer, 18=Basketball, 13=Tennis")):
    """
    Retorna partidas ao vivo via BetsAPI.
    sport_id=1 para futebol (padrão).
    """
    data = await _betsapi_get("events/inplay", {"sport_id": sport_id})
    results = data.get("results", [])

    # Formata para o frontend
    matches = []
    for r in results:
        matches.append({
            "event_id":   r.get("id"),
            "league":     r.get("league", {}).get("name", ""),
            "home_team":  r.get("home", {}).get("name", ""),
            "away_team":  r.get("away", {}).get("name", ""),
            "score":      r.get("ss", ""),
            "time":       r.get("timer", {}).get("tm", ""),
            "status":     r.get("time_status", ""),
        })

    return {"total": len(matches), "matches": matches}


@app.get("/live/match/{event_id}")
async def get_live_match_detail(event_id: str):
    """
    Retorna detalhes de uma partida ao vivo, incluindo odds.
    Combina com histórico StatsBomb para enriquecer o contexto.
    """
    # Dados da partida ao vivo
    data = await _betsapi_get("event/view", {"event_id": event_id})
    event = data.get("results", [{}])[0]

    # Extrai placar atual
    score = event.get("ss", "0-0")
    try:
        home_score, away_score = map(int, score.split("-"))
    except Exception:
        home_score, away_score = 0, 0

    score_diff = home_score - away_score

    # Odds (se disponível)
    odds_data = await _betsapi_get("event/odds/summary", {"event_id": event_id})

    return {
        "event_id":  event_id,
        "home_team": event.get("home", {}).get("name", ""),
        "away_team": event.get("away", {}).get("name", ""),
        "score":     score,
        "minute":    event.get("timer", {}).get("tm", 0),
        "score_diff": score_diff,
        "odds":      odds_data.get("results", {}),
        "tip": (
            "Use /predict/match para analisar probabilidades baseadas em estatísticas históricas. "
            "Combine com os dados ao vivo para contexto completo."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS Telegram — Bot Betina I.A.
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/telegram/status")
async def telegram_status():
    """Status do bot Telegram: configuração, chats registrados e envios do dia."""
    return {
        "configured": telegram_is_configured(),
        "registered_chats": len(get_registered_chats()),
        "daily_sends": get_daily_sends_count(),
        "max_daily": 3,
    }


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    Webhook que o Telegram chama quando alguém manda mensagem.
    Processa a mensagem e responde diretamente via Bot API.

    Configure via:
        POST https://api.telegram.org/bot<TOKEN>/setWebhook
        {"url": "https://seu-dominio.com/telegram/webhook"}
    """
    body = await request.json()

    # Extrai mensagem do payload do Telegram
    message = body.get("message", {})
    if not message:
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return {"ok": True}

    logger.info(f"Telegram recebido de chat {chat_id}: {text}")

    # Processa e responde
    response_text = await handle_incoming_message(text, chat_id=chat_id)
    await send_telegram_message(chat_id, response_text)

    return {"ok": True}


@app.get("/telegram/registered")
async def list_registered():
    """Lista chats registrados para alertas."""
    return {
        "chats": get_registered_chats(),
        "count": len(get_registered_chats()),
        "daily_sends": get_daily_sends_count(),
    }


