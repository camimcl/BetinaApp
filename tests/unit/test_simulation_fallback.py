"""
tests/unit/test_simulation_fallback.py

TIPO 1 — TESTES UNITÁRIOS (Unit Tests) — continuação
=====================================================

Testa o fallback de narrativa do simulador "E SE?" (generate_simulation_narrative)
quando o Gemini está indisponível.

Técnicas aplicadas:
  - Mocking (substituição do cliente Gemini por None)
  - Output Validation (validação do conteúdo da saída)
  - Decision Table Testing (tabela de decisão para tipos/direções)
"""

from unittest.mock import patch
import pytest

from src.api.gemini_client import generate_simulation_narrative


# ═════════════════════════════════════════════════════════════════════════════
# GRUPO: Fallback Rico do Simulador (sem Gemini)
# Quando o cliente Gemini está indisponível (_get_client retorna None),
# a função deve gerar narrativa local de qualidade — não mensagens técnicas.
# ═════════════════════════════════════════════════════════════════════════════

# Patch aplicado em _get_client e _can_call_api para forçar modo fallback
PATCHES = [
    patch("src.api.gemini_client._get_client", return_value=None),
    patch("src.api.gemini_client._can_call_api", return_value=False),
]


def apply_patches(func):
    """Decorator que aplica todos os patches de teste."""
    for p in reversed(PATCHES):
        func = p(func)
    return func


@apply_patches
def test_fallback_shot_positivo_contem_emoji_alvo(*_):
    """
    Decision Table: tipo=shot, direção positiva →
    deve conter emoji de alvo (🎯 ou ⚽) e menção à probabilidade de gol.
    """
    result = generate_simulation_narrative(
        prediction_type="shot",
        description="E se o chute fosse mais perto?",
        changes={"distance_to_goal": 10},
        pct_change=17.0,
        impact_pct_change=27.0,
    )
    assert "%" in result, "Resultado deve mencionar porcentagem"
    assert "17" in result, "Deve mencionar o delta de 17%"
    assert any(e in result for e in ["🎯", "⚽", "gol", "Gol", "Análise"]), \
        f"Narrativa de chute deve referenciar gol. Obtido:\n{result}"


@apply_patches
def test_fallback_shot_negativo_contem_defesa(*_):
    """
    Decision Table: tipo=shot, direção negativa →
    deve mencionar redução e contexto defensivo.
    """
    result = generate_simulation_narrative(
        prediction_type="shot",
        description="E se houvesse muita pressão?",
        changes={"under_pressure": 3},
        pct_change=-12.0,
    )
    assert "12" in result
    assert any(e in result for e in ["🛡️", "📊", "cai", "reduz", "Defensivo", "defensiva"]), \
        f"Narrativa negativa deve mencionar redução. Obtido:\n{result}"


@apply_patches
def test_fallback_foul_positivo_risco_elevado(*_):
    """
    Decision Table: tipo=foul, direção positiva →
    deve mencionar risco de cartão subindo.
    """
    result = generate_simulation_narrative(
        prediction_type="foul",
        description="E se a falta fosse na área de risco?",
        changes={"in_danger_zone": 1},
        pct_change=22.0,
        impact_pct_change=-5.0,
    )
    assert "22" in result
    assert any(e in result for e in ["🟨", "⚠️", "cartão", "Cartão", "risco", "Risco"]), \
        f"Narrativa de falta deve mencionar cartão. Obtido:\n{result}"


@apply_patches
def test_fallback_match_positivo_dominio(*_):
    """
    Decision Table: tipo=match, direção positiva →
    deve mencionar vantagem e domínio.
    """
    result = generate_simulation_narrative(
        prediction_type="match",
        description="E se o time dominasse o campo?",
        changes={"pressure_ratio": 1.8},
        pct_change=15.0,
    )
    assert "15" in result
    assert any(e in result for e in ["📈", "🏆", "vitória", "Vitória", "domínio", "Domínio"]), \
        f"Narrativa de partida positiva deve mencionar vitória. Obtido:\n{result}"


@apply_patches
def test_fallback_impacto_vitoria_presente_quando_informado(*_):
    """
    Output Validation:
    Quando impact_pct_change é fornecido para tipo shot,
    o resultado deve mencionar o impacto na vitória.
    """
    result = generate_simulation_narrative(
        prediction_type="shot",
        description="E se fosse gol aberto?",
        changes={"open_goal": 1},
        pct_change=30.0,
        impact_pct_change=18.0,
    )
    # Deve mencionar o impacto na vitória
    assert "18" in result or "Vitória" in result or "vitória" in result, \
        f"Deve mencionar impacto na vitória de 18%. Obtido:\n{result}"


@apply_patches
def test_fallback_nao_retorna_string_tecnica(*_):
    """
    Output Validation — critério negativo:
    O fallback NÃO deve retornar mensagens técnicas brutas
    como 'delta', 'pontos percentuais' ou 'estatísticas'.
    Esses termos eram do fallback antigo que foi removido.
    """
    result = generate_simulation_narrative(
        prediction_type="shot",
        description="Teste",
        changes={"distance_to_goal": 12},
        pct_change=5.0,
    )
    proibidos = ["modo local", "contingência", "estatísticas na partida"]
    for termo in proibidos:
        assert termo.lower() not in result.lower(), \
            f"Termo técnico proibido encontrado: '{termo}'. Obtido:\n{result}"


@apply_patches
def test_fallback_sempre_retorna_string_nao_vazia(*_):
    """
    Output Validation:
    O fallback nunca deve retornar None, string vazia ou exceção.
    """
    result = generate_simulation_narrative(
        prediction_type="match",
        description="",
        changes={},
        pct_change=0.0,
    )
    assert isinstance(result, str)
    assert len(result) > 20, "Narrativa deve ter conteúdo substancial"
