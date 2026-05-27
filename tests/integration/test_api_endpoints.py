"""
tests/integration/test_api_endpoints.py

TIPO 2 — TESTES DE INTEGRAÇÃO (Integration Tests)
==================================================

Objetivo: verificar se os componentes do sistema funcionam JUNTOS —
especificamente se os endpoints da API FastAPI aceitam requests HTTP reais,
processam os dados corretamente através das camadas (rota → predictor → resposta)
e retornam contratos de resposta válidos.

A diferença do teste unitário: aqui testamos o sistema INTEGRADO,
com todas as suas camadas conversando entre si.
Os modelos ML são mockados para isolamento do sistema externo de arquivos.

Técnicas aplicadas:
  - Contract Testing (verificação do contrato de interface da API)
  - Black-Box Testing (testa inputs/outputs sem conhecer o interior)
  - Mocking de dependências externas (modelos ML, Gemini, API Football)
  - Happy Path + Error Path
"""

import json
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ─── Importa a aplicação FastAPI ─────────────────────────────────────────────
from src.api.main import app


# ─── Fixture: mock dos modelos ML ────────────────────────────────────────────

def _make_mock_model(proba_output):
    """Cria um mock de modelo sklearn com predict_proba configurado."""
    mock = MagicMock()
    mock.predict_proba.return_value = np.array([proba_output])
    return mock


def _make_mock_explainer(n_features=10):
    """Cria um mock do SHAP explainer."""
    mock = MagicMock()
    mock.shap_values.return_value = np.zeros(n_features)
    return mock


# Artifact de modelo mockado — mesma estrutura que o predictor.py espera
MOCK_GOAL_ARTIFACT = {
    "model":        _make_mock_model([0.85, 0.15]),       # [P(não gol), P(gol)]
    "encoders":     {},
    "feature_cols": ["distance_to_goal", "angle_to_goal", "xg",
                     "under_pressure", "first_time", "open_goal",
                     "minute", "score_diff", "is_second_half",
                     "is_extra_time"],
    "cat_cols":     ["technique", "body_part", "shot_type"],
    "class_names":  ["no_goal", "goal"],
    "explainer":    _make_mock_explainer(10),
}

MOCK_CARD_ARTIFACT = {
    "model":        _make_mock_model([0.60, 0.40]),
    "encoders":     {},
    "feature_cols": ["x", "y", "dist_to_center", "in_danger_zone",
                     "in_final_third", "minute", "under_pressure",
                     "score_diff", "team_losing", "is_second_half"],
    "cat_cols":     ["foul_type"],
    "class_names":  ["no_card", "card"],
    "explainer":    _make_mock_explainer(10),
}

MOCK_MATCH_ARTIFACT = {
    "model":        _make_mock_model([0.55, 0.25, 0.20]),  # [home, draw, away]
    "encoders":     {},
    "feature_cols": ["home_xg", "away_xg", "xg_diff", "home_shots",
                     "away_shots", "home_shots_ot", "away_shots_ot",
                     "home_pass_acc", "away_pass_acc", "pressure_ratio",
                     "home_fouls", "away_fouls"],
    "cat_cols":     [],
    "class_names":  ["home_win", "draw", "away_win"],
    "explainer":    _make_mock_explainer(12),
}

MOCK_MODELS = {
    "goal_model":  MOCK_GOAL_ARTIFACT,
    "card_model":  MOCK_CARD_ARTIFACT,
    "match_model": MOCK_MATCH_ARTIFACT,
}


@pytest.fixture
def client():
    """
    Cliente de teste do FastAPI com modelos ML e Gemini mockados.
    Garante que os testes rodem sem dependências externas.
    """
    with patch("src.models.predictor._MODELS", MOCK_MODELS), \
         patch("src.api.gemini_client._get_client", return_value=None), \
         patch("src.api.gemini_client._can_call_api", return_value=False), \
         patch("src.api.scheduler.start_proactive_scheduler", return_value=None):
        yield TestClient(app)


# ═════════════════════════════════════════════════════════════════════════════
# GRUPO 1: /health — Verificação de Saúde da API
# ═════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:
    """
    Contract Testing: verifica se /health sempre responde com o contrato esperado.
    Endpoint crítico para monitoramento da aplicação em produção.
    """

    def test_health_retorna_200(self, client):
        """Happy Path: /health deve retornar HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_contem_campo_status(self, client):
        """O corpo deve conter o campo 'status'."""
        data = client.get("/health").json()
        assert "status" in data

    def test_health_status_ok(self, client):
        """O campo status deve ser 'ok'."""
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_contem_models_loaded(self, client):
        """Contract: campo 'models_loaded' deve estar presente."""
        data = client.get("/health").json()
        assert "models_loaded" in data
        assert isinstance(data["models_loaded"], bool)

    def test_health_contem_football_api_configured(self, client):
        """Contract: campo 'football_api_configured' deve estar presente."""
        data = client.get("/health").json()
        assert "football_api_configured" in data


# ═════════════════════════════════════════════════════════════════════════════
# GRUPO 2: POST /predict/shot — Predição de Chute
# ═════════════════════════════════════════════════════════════════════════════

SHOT_PAYLOAD = {
    "distance_to_goal": 15.0,
    "angle_to_goal": 30.0,
    "xg": 0.12,
    "technique": "Normal",
    "body_part": "Right Foot",
    "shot_type": "Open Play",
    "first_time": 0,
    "open_goal": 0,
    "follows_dribble": 0,
    "under_pressure": 1,
    "minute": 45.0,
    "time_seconds": 2700.0,
    "is_second_half": 0,
    "is_extra_time": 0,
    "score_diff": 0,
    "is_home_team": 1,
}


class TestPredictShotEndpoint:
    """
    Black-Box Testing do endpoint de predição de chute:
    valida inputs/outputs sem se preocupar com a implementação interna.
    """

    def test_predict_shot_retorna_200(self, client):
        """Happy Path: payload válido deve retornar HTTP 200."""
        r = client.post("/predict/shot", json=SHOT_PAYLOAD)
        assert r.status_code == 200, f"Esperado 200, obtido {r.status_code}: {r.text}"

    def test_predict_shot_contem_goal_probability(self, client):
        """Contract: resposta deve conter 'goal_probability'."""
        data = client.post("/predict/shot", json=SHOT_PAYLOAD).json()
        assert "goal_probability" in data

    def test_predict_shot_probabilidade_entre_0_e_1(self, client):
        """A probabilidade de gol deve estar no intervalo [0, 1]."""
        data = client.post("/predict/shot", json=SHOT_PAYLOAD).json()
        prob = data["goal_probability"]
        assert 0.0 <= prob <= 1.0, f"Probabilidade fora do intervalo: {prob}"

    def test_predict_shot_contem_factors(self, client):
        """Resposta deve conter lista de fatores SHAP explicativos."""
        data = client.post("/predict/shot", json=SHOT_PAYLOAD).json()
        assert "factors" in data
        assert isinstance(data["factors"], list)

    def test_predict_shot_contem_narrative(self, client):
        """Resposta deve incluir narrativa textual para o usuário."""
        data = client.post("/predict/shot", json=SHOT_PAYLOAD).json()
        assert "narrative" in data
        assert isinstance(data["narrative"], str)
        assert len(data["narrative"]) > 0

    def test_predict_shot_payload_invalido_retorna_422(self, client):
        """
        Error Path:
        Payload sem campos obrigatórios deve retornar HTTP 422 (Unprocessable Entity).
        """
        r = client.post("/predict/shot", json={"distance_to_goal": 15.0})  # faltam campos
        assert r.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# GRUPO 3: POST /predict/match — Predição de Resultado
# ═════════════════════════════════════════════════════════════════════════════

MATCH_PAYLOAD = {
    "home_team_name": "Flamengo",
    "away_team_name": "Corinthians",
    "home_score": 1,
    "away_score": 0,
    "minute": 60,
    "home_xg": 1.8,
    "away_xg": 0.9,
    "xg_diff": 0.9,
    "home_shots": 12,
    "away_shots": 7,
    "home_shots_ot": 5,
    "away_shots_ot": 2,
    "home_passes": 450,
    "away_passes": 320,
    "home_pass_acc": 0.84,
    "away_pass_acc": 0.78,
    "home_pressures": 120,
    "away_pressures": 90,
    "pressure_ratio": 1.33,
    "home_fouls": 10,
    "away_fouls": 14,
}


class TestPredictMatchEndpoint:
    """Testa o endpoint de predição de resultado de partida."""

    def test_predict_match_retorna_200(self, client):
        r = client.post("/predict/match", json=MATCH_PAYLOAD)
        assert r.status_code == 200

    def test_predict_match_soma_probabilidades_1(self, client):
        """
        Contract Test crítico:
        home_win + draw + away_win deve somar aproximadamente 1.0.
        """
        data = client.post("/predict/match", json=MATCH_PAYLOAD).json()
        total = (
            data["home_win_probability"]
            + data["draw_probability"]
            + data["away_win_probability"]
        )
        assert abs(total - 1.0) < 0.01, f"Probabilidades não somam 1: {total}"

    def test_predict_match_contem_nomes_times(self, client):
        """Resposta deve preservar os nomes dos times enviados."""
        data = client.post("/predict/match", json=MATCH_PAYLOAD).json()
        assert data.get("home_team_name") == "Flamengo"
        assert data.get("away_team_name") == "Corinthians"

    def test_predict_match_contem_dominant_outcome(self, client):
        """Resposta deve indicar o resultado mais provável."""
        data = client.post("/predict/match", json=MATCH_PAYLOAD).json()
        assert "dominant_outcome" in data
        assert data["dominant_outcome"] in ["home_win", "draw", "away_win"]


# ═════════════════════════════════════════════════════════════════════════════
# GRUPO 4: POST /simulate — Motor "E SE?"
# ═════════════════════════════════════════════════════════════════════════════

SIMULATE_PAYLOAD = {
    "prediction_type": "shot",
    "base_data": {
        "distance_to_goal": 25.0, "angle_to_goal": 20.0, "xg": 0.07,
        "technique": "Normal", "body_part": "Right Foot", "shot_type": "Open Play",
        "first_time": 0, "open_goal": 0, "follows_dribble": 0, "under_pressure": 1,
        "minute": 70.0, "time_seconds": 4200.0, "is_second_half": 1,
        "is_extra_time": 0, "score_diff": 0, "is_home_team": 1,
        "home_score": 0, "away_score": 0,
    },
    "overrides": {"distance_to_goal": 10.0, "under_pressure": 0},
    "description": "E se o chute fosse mais perto e sem pressão?",
}


class TestSimulateEndpoint:
    """
    Testa o motor de simulação hipotética (cenário base vs cenário simulado).
    Este é o endpoint central do produto — o "coração" do IntelliBet.
    """

    def test_simulate_retorna_200(self, client):
        r = client.post("/simulate", json=SIMULATE_PAYLOAD)
        assert r.status_code == 200, f"Erro: {r.text}"

    def test_simulate_contem_base_e_simulated(self, client):
        """Contract: resposta deve ter 'base' e 'simulated' para comparação."""
        data = client.post("/simulate", json=SIMULATE_PAYLOAD).json()
        assert "base" in data
        assert "simulated" in data

    def test_simulate_contem_delta(self, client):
        """Contract: deve retornar o delta (diferença) entre os cenários."""
        data = client.post("/simulate", json=SIMULATE_PAYLOAD).json()
        assert "delta" in data
        assert isinstance(data["delta"], dict)

    def test_simulate_contem_narrative(self, client):
        """A narrativa do simulador deve ser uma string não-vazia."""
        data = client.post("/simulate", json=SIMULATE_PAYLOAD).json()
        assert "narrative" in data
        assert len(data["narrative"]) > 10

    def test_simulate_tipo_invalido_retorna_erro(self, client):
        """
        Error Path:
        Tipo de simulação inválido deve retornar HTTP 4xx ou 5xx.
        """
        payload = {**SIMULATE_PAYLOAD, "prediction_type": "invalido"}
        r = client.post("/simulate", json=payload)
        assert r.status_code in [400, 422, 500], \
            f"Tipo inválido deveria falhar, obtido {r.status_code}"
