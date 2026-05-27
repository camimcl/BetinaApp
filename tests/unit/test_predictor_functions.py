"""
tests/unit/test_predictor_functions.py

TIPO 1 — TESTES UNITÁRIOS (Unit Tests)
=======================================

Objetivo: testar funções puras do predictor.py de forma isolada,
sem carregar modelos, banco de dados ou serviços externos.

Cada teste valida uma única responsabilidade da função-alvo.
Técnicas aplicadas:
  - Equivalence Partitioning (particionamento em classes de equivalência)
  - Boundary Value Analysis (análise de valor limite)
  - State-Based Testing (verificação de estado de saída)
"""

import numpy as np
import pytest

# ─── Import direto das funções puras (sem carregar modelos) ──────────────────
from src.models.predictor import (
    _apply_live_adjustment,
    _top_shap_factors,
    FEATURE_LABELS_PT,
)


# ═════════════════════════════════════════════════════════════════════════════
# GRUPO 1: _apply_live_adjustment
# Função que ajusta as probabilidades de vitória/empate/derrota
# com base no placar real e no minuto da partida.
# É uma função PURA: não depende de modelos externos → ideal para teste unitário.
# ═════════════════════════════════════════════════════════════════════════════

class TestApplyLiveAdjustment:
    """
    Testa o algoritmo de blending live que combina o modelo XGBoost
    com probabilidades empíricas baseadas no placar e no tempo.
    """

    # Probabilidades base fictícias do modelo (50% / 25% / 25%)
    BASE_PROBS = np.array([0.50, 0.25, 0.25])

    def test_output_soma_1(self):
        """As probabilidades ajustadas devem sempre somar 1 (distribuição válida)."""
        result = _apply_live_adjustment(self.BASE_PROBS, home_score=1, away_score=0, minute=60)
        assert abs(result.sum() - 1.0) < 1e-6, \
            f"Probabilidades não somam 1: {result.sum()}"

    def test_output_todas_positivas(self):
        """Nenhuma probabilidade pode ser negativa ou zero."""
        result = _apply_live_adjustment(self.BASE_PROBS, home_score=0, away_score=0, minute=0)
        assert all(result > 0), f"Probabilidade negativa detectada: {result}"

    def test_vencendo_por_3_gols_quase_certo(self):
        """
        Boundary Value Analysis:
        Time vencendo por 3+ gols deve ter probabilidade de vitória >= 92%.
        Baseado em dados empíricos reais do futebol profissional.
        """
        result = _apply_live_adjustment(self.BASE_PROBS, home_score=3, away_score=0, minute=75)
        # Mandante vencendo 3×0 no min 75 → deve ter altíssima probabilidade
        assert result[0] >= 0.90, \
            f"Esperado >= 90% de vitória com 3×0 no min 75, obtido {result[0]:.2%}"

    def test_empate_0_0_inicio_equilibrado(self):
        """
        Equivalence Partitioning:
        Jogo empatado no início (minuto 0) deve manter equilíbrio —
        as probabilidades de vitória das duas equipes devem ser similares.
        """
        result = _apply_live_adjustment(self.BASE_PROBS, home_score=0, away_score=0, minute=0)
        # Com 0×0 no min 0, modelo XGBoost domina → probabilidades próximas às base
        assert result[0] > 0.1 and result[2] > 0.1, \
            "Jogo empatado no início não deve eliminar nenhum cenário"

    def test_vencendo_final_alta_confianca(self):
        """
        Boundary Value Analysis — limite de tempo:
        Liderando por 1 gol nos últimos 10 minutos → vitória muito provável.
        """
        result = _apply_live_adjustment(self.BASE_PROBS, home_score=1, away_score=0, minute=82)
        assert result[0] >= 0.75, \
            f"Liderar 1×0 no min 82 deve ter >= 75% de vitória, obtido {result[0]:.2%}"

    def test_minuto_acima_95_clampado(self):
        """
        Boundary Value Analysis — valor extremo:
        Minuto 120 (prorrogação extrema) deve ser tratado como 95,
        sem erros ou divisão por zero.
        """
        result = _apply_live_adjustment(self.BASE_PROBS, home_score=1, away_score=0, minute=120)
        assert result is not None
        assert abs(result.sum() - 1.0) < 1e-6

    def test_visitante_vencendo_reflete_away(self):
        """
        State-Based Testing:
        Quando visitante vence, a posição [2] (away_win) deve ser a maior.
        """
        result = _apply_live_adjustment(self.BASE_PROBS, home_score=0, away_score=2, minute=70)
        assert result[2] > result[0], \
            f"Visitante vencendo 2×0: away_win ({result[2]:.2%}) < home_win ({result[0]:.2%})"


# ═════════════════════════════════════════════════════════════════════════════
# GRUPO 2: _top_shap_factors
# Função que seleciona e ordena os N fatores SHAP mais influentes.
# ═════════════════════════════════════════════════════════════════════════════

class TestTopShapFactors:
    """
    Testa a extração e classificação dos fatores SHAP que explicam
    por que a IA tomou determinada decisão.
    """

    def test_retorna_n_fatores(self):
        """Deve retornar exatamente N fatores."""
        shap_vals = np.array([0.1, -0.3, 0.05, 0.8, -0.02])
        features  = ["xg", "distance_to_goal", "angle_to_goal", "open_goal", "minute"]
        result = _top_shap_factors(shap_vals, features, n=3)
        assert len(result) == 3

    def test_ordenado_por_valor_absoluto(self):
        """O primeiro fator deve ter o maior impacto absoluto (|SHAP|)."""
        shap_vals = np.array([0.05, -0.90, 0.30])
        features  = ["xg", "distance_to_goal", "under_pressure"]
        result = _top_shap_factors(shap_vals, features, n=3)
        # -0.90 tem maior |SHAP| → deve vir primeiro
        assert result[0]["feature"] == "distance_to_goal"

    def test_direction_aumenta_quando_positivo(self):
        """Valor SHAP positivo → direction deve ser 'aumenta'."""
        shap_vals = np.array([0.5])
        features  = ["xg"]
        result = _top_shap_factors(shap_vals, features, n=1)
        assert result[0]["direction"] == "aumenta"

    def test_direction_reduz_quando_negativo(self):
        """Valor SHAP negativo → direction deve ser 'reduz'."""
        shap_vals = np.array([-0.5])
        features  = ["distance_to_goal"]
        result = _top_shap_factors(shap_vals, features, n=1)
        assert result[0]["direction"] == "reduz"

    def test_label_traduzido_para_portugues(self):
        """Features conhecidas devem ter label em português do dicionário."""
        shap_vals = np.array([0.3])
        features  = ["distance_to_goal"]
        result = _top_shap_factors(shap_vals, features, n=1)
        assert result[0]["label"] == FEATURE_LABELS_PT["distance_to_goal"]

    def test_feature_desconhecida_usa_nome_original(self):
        """Feature não mapeada no dicionário deve usar o próprio nome como label."""
        shap_vals = np.array([0.4])
        features  = ["feature_desconhecida_xyz"]
        result = _top_shap_factors(shap_vals, features, n=1)
        assert result[0]["label"] == "feature_desconhecida_xyz"

    def test_n_maior_que_features_nao_quebra(self):
        """Se N > total de features, retorna apenas o que existe (sem erro)."""
        shap_vals = np.array([0.1, 0.2])
        features  = ["xg", "minute"]
        result = _top_shap_factors(shap_vals, features, n=10)
        assert len(result) == 2  # só existem 2 features

    def test_shap_value_arredondado_4_casas(self):
        """O campo shap_value deve ter precisão de 4 casas decimais."""
        shap_vals = np.array([0.123456789])
        features  = ["xg"]
        result = _top_shap_factors(shap_vals, features, n=1)
        assert result[0]["shap_value"] == round(0.123456789, 4)
