"""
src/models/predictor.py

Carrega os modelos treinados e expõe métodos de predição + simulação.

Funções principais:
  - predict_shot(shot_data)      → P(gol) + explicação SHAP
  - predict_foul(foul_data)      → P(cartão) + explicação SHAP
  - predict_match(match_data)    → P(resultado) + explicação SHAP
  - simulate_what_if(base, overrides) → cenário hipotético

O NarrativeGenerator converte valores SHAP em frases em português,
tornando cada predição explicável para o usuário final.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
import shap

# Usando fallback local se o arquivo ainda estiver sendo reformado, mas idealmente importa o gemini:
from src.api.gemini_client import generate_simulation_narrative

MODELS_DIR = Path(os.getenv("MODELS_DIR", "data/models"))

# Cache dos modelos em memória (carregados uma vez na inicialização)
_MODELS: Dict[str, Any] = {}


def load_models():
    """Carrega todos os modelos do disco para memória."""
    global _MODELS
    for name in ["goal_model", "card_model", "match_model"]:
        path = MODELS_DIR / f"{name}.pkl"
        if path.exists():
            _MODELS[name] = joblib.load(path)
        else:
            raise FileNotFoundError(
                f"Modelo '{name}' não encontrado em {path}. "
                "Execute `python src/models/train.py` primeiro."
            )


def _get_model(name: str) -> dict:
    if not _MODELS:
        load_models()
    return _MODELS[name]


# ══════════════════════════════════════════════════════════════════════════════
# NARRATIVA — Converte SHAP em linguagem humana
# ══════════════════════════════════════════════════════════════════════════════

FEATURE_LABELS_PT = {
    # Shot model
    "distance_to_goal":  "distância ao gol",
    "angle_to_goal":     "ângulo de visão do gol",
    "xg":                "qualidade da chance",
    "technique":         "técnica do chute",
    "body_part":         "parte do corpo usada",
    "shot_type":         "tipo de jogada",
    "first_time":        "chute de primeira",
    "open_goal":         "gol aberto (sem goleiro)",
    "follows_dribble":   "após drible",
    "under_pressure":    "sob pressão da defesa",
    "score_diff":        "diferença no placar",
    "minute":            "minuto da partida",
    "is_second_half":    "segundo tempo",
    "is_extra_time":     "prorrogação",
    # Card model
    "in_danger_zone":    "falta perto da área",
    "in_final_third":    "falta no campo ofensivo",
    "foul_type":         "tipo de falta",
    "team_losing":       "time perdendo",
    "is_last_10_min":    "últimos 10 minutos",
    # Match model — SEM jargão técnico
    "home_xg":           "chances claras de gol (mandante)",
    "away_xg":           "chances claras de gol (visitante)",
    "xg_diff":           "diferença de oportunidades de gol",
    "home_xg_sot":       "chances de gol (mandante)",
    "away_xg_sot":       "chances de gol (visitante)",
    "home_shots":        "total de chutes (mandante)",
    "away_shots":        "total de chutes (visitante)",
    "home_shots_ot":     "chutes no alvo (mandante)",
    "away_shots_ot":     "chutes no alvo (visitante)",
    "shot_ratio":        "proporção de chutes entre os times",
    "home_pass_acc":     "precisão de passes (mandante)",
    "away_pass_acc":     "precisão de passes (visitante)",
    "pass_acc_diff":     "diferença de precisão de passes",
    "home_pressures":    "pressão no adversário (mandante)",
    "away_pressures":    "pressão no adversário (visitante)",
    "pressure_ratio":    "domínio territorial",
    "home_fouls":        "faltas cometidas (mandante)",
    "away_fouls":        "faltas cometidas (visitante)",
    "home_carries":      "conduções com bola (mandante)",
    "away_carries":      "conduções com bola (visitante)",
}


def _top_shap_factors(shap_vals: np.ndarray, feature_names: list, n: int = 3) -> List[Dict]:
    """Retorna os N fatores SHAP mais influentes (positivos e negativos)."""
    pairs = sorted(zip(shap_vals, feature_names), key=lambda x: abs(x[0]), reverse=True)
    factors = []
    for val, feat in pairs[:n]:
        factors.append({
            "feature": feat,
            "label": FEATURE_LABELS_PT.get(feat, feat),
            "shap_value": round(float(val), 4),
            "direction": "aumenta" if val > 0 else "reduz",
        })
    return factors


def _narrative_goal(prob: float, factors: List[Dict], shot_data: dict) -> str:
    """Gera narrativa em português para predição de gol."""
    pct = round(prob * 100, 1)

    # Qualificador
    if pct >= 70:
        qualifier = "altíssima"
    elif pct >= 40:
        qualifier = "considerável"
    elif pct >= 20:
        qualifier = "moderada"
    else:
        qualifier = "baixa"

    lines = [f"**Probabilidade de gol: {pct}%** — chance {qualifier}."]

    # Principais fatores
    for f in factors[:2]:
        lines.append(
            f"• {f['label'].capitalize()} **{f['direction']}** a chance "
            f"(impacto SHAP: {abs(f['shap_value']):.3f})"
        )

    # Contexto xG
    xg = shot_data.get("xg")
    if xg:
        lines.append(
            f"• O xG (Expected Goals) do StatsBomb para este chute é **{xg:.3f}**, "
            f"{'alinhado' if abs(prob - xg) < 0.1 else 'ajustado'} pelo contexto da partida."
        )

    return "\n".join(lines)


def _narrative_card(prob: float, factors: List[Dict], foul_data: dict) -> str:
    """Gera narrativa em português para predição de cartão."""
    pct = round(prob * 100, 1)

    if pct >= 60:
        qualifier = "alto"
    elif pct >= 30:
        qualifier = "moderado"
    else:
        qualifier = "baixo"

    lines = [f"**Probabilidade de cartão: {pct}%** — risco {qualifier}."]

    for f in factors[:2]:
        lines.append(
            f"• {f['label'].capitalize()} **{f['direction']}** o risco de cartão "
            f"(impacto: {abs(f['shap_value']):.3f})"
        )

    minute = foul_data.get("minute", 0)
    if minute >= 80:
        lines.append("• Falta nos minutos finais — árbitros tendem a ser mais rigorosos.")

    return "\n".join(lines)


def _narrative_match(
    probs: np.ndarray,
    factors: List[Dict],
    home_name: str = "Mandante",
    away_name: str = "Visitante",
    match_stats: dict = None,
) -> str:
    """
    Gera narrativa de resultado. Tenta Gemini primeiro;
    fallback local contextualizado e variado se Gemini indisponível.
    """
    import random

    # Converte numpy float32 → inteiro (sem casas decimais)
    home_pct = round(float(probs[0]) * 100)
    draw_pct = round(float(probs[1]) * 100)
    away_pct = round(float(probs[2]) * 100)

    # Tenta Gemini primeiro
    try:
        from src.api.gemini_client import generate_match_narrative
        gemini_text = generate_match_narrative(
            home_name=home_name,
            away_name=away_name,
            home_pct=home_pct,
            draw_pct=draw_pct,
            away_pct=away_pct,
            match_stats=match_stats or {},
            factors=factors,
        )
        if gemini_text:
            return gemini_text
    except Exception:
        pass

    # ── Fallback local rico (sem Gemini) ──────────────────────────────────
    stats = match_stats or {}

    # Identifica resultado mais provável
    ranked = sorted(
        [(home_pct, home_name, "home"), (draw_pct, "Empate", "draw"), (away_pct, away_name, "away")],
        key=lambda x: x[0], reverse=True
    )
    best_pct, best_label, best_type = ranked[0]
    sec_pct,  sec_label,  _         = ranked[1]
    thr_pct,  thr_label,  _         = ranked[2]
    gap = best_pct - sec_pct

    # Extrai estatísticas com conversão segura
    h_shots = int(stats.get("home_shots", 0))
    a_shots = int(stats.get("away_shots", 0))
    h_sot   = int(stats.get("home_shots_ot", 0))
    a_sot   = int(stats.get("away_shots_ot", 0))
    h_pa    = round(float(stats.get("home_pass_acc", 0)) * 100)
    a_pa    = round(float(stats.get("away_pass_acc", 0)) * 100)
    pr      = float(stats.get("pressure_ratio", 1.0))
    h_fouls = int(stats.get("home_fouls", 0))
    a_fouls = int(stats.get("away_fouls", 0))

    # ── Bloco 1: Cenário favorito ──────────────────────────────────────────
    if best_type == "draw":
        intro = (
            f"⚖️ **Jogo em equilíbrio total** — os dados apontam **{best_pct}%** de probabilidade de empate. "
            f"Nenhum dos times demonstra domínio suficiente para se isolar como favorito neste momento."
        )
    elif gap >= 20:
        intro = (
            f"🎯 **{best_label}** chega como grande favorito, com **{best_pct}%** de probabilidade de vitória — "
            f"vantagem expressiva sobre {sec_label} ({sec_pct}%) e {thr_label} ({thr_pct}%). "
            f"A tendência ofensiva está claramente inclinada para um lado."
        )
    elif gap >= 8:
        intro = (
            f"⚔️ **{best_label}** apresenta vantagem com **{best_pct}%** de probabilidade, "
            f"mas **{sec_label}** ({sec_pct}%) mantém o jogo em aberto. "
            f"Margem considerável, porém não definitiva."
        )
    else:
        intro = (
            f"⚖️ Partida de difícil previsão — **{home_name}** com {home_pct}%, **Empate** com {draw_pct}% "
            f"e **{away_name}** com {away_pct}%. Qualquer resultado é tecnicamente possível neste momento."
        )

    # ── Bloco 2: Insight tático ────────────────────────────────────────────
    insight_parts = []

    if h_sot or a_sot:
        if h_sot > a_sot:
            insight_parts.append(
                f"**{home_name}** criou mais perigo real, com **{h_sot} finalizações no alvo** "
                f"contra apenas {a_sot} do **{away_name}** — a eficiência ofensiva pesa a favor da casa."
            )
        elif a_sot > h_sot:
            insight_parts.append(
                f"**{away_name}** surpreende com **{a_sot} chutes certeiros** frente a {h_sot} do **{home_name}** — "
                f"qualidade ofensiva que eleva sua probabilidade mesmo jogando fora."
            )
        else:
            insight_parts.append(
                f"Equilíbrio também nas finalizações — **{home_name}** e **{away_name}** com {h_sot} chutes no alvo cada."
            )

    if h_pa and a_pa:
        if h_pa > a_pa + 5:
            insight_parts.append(
                f"A circulação de bola do **{home_name}** é determinante: **{h_pa}%** de precisão nos passes "
                f"contra **{a_pa}%** do adversário — controle que se converte em oportunidades."
            )
        elif a_pa > h_pa + 5:
            insight_parts.append(
                f"O **{away_name}** dita o ritmo com **{a_pa}%** de precisão de passe, "
                f"superior aos **{h_pa}%** do **{home_name}** — domínio técnico notável."
            )

    if pr > 1.2:
        insight_parts.append(
            f"O **{home_name}** exerce pressão constante sobre a saída de bola adversária — controle territorial inequívoco."
        )
    elif pr < 0.8:
        insight_parts.append(
            f"O **{away_name}** impressiona pela intensidade territorial, mesmo jogando fora — desgaste evidente no rival."
        )

    if not insight_parts:
        insight_parts.append(
            f"A consistência das ações ofensivas e o padrão de jogo observado posicionam **{best_label}** à frente nesta leitura."
        )

    insight_block = "📊 **Por que esse favoritismo?**\n\n" + " ".join(insight_parts)

    # ── Bloco 3: Radar Betina ──────────────────────────────────────────────
    radar_parts = []
    total_shots = h_shots + a_shots

    if total_shots > 14:
        radar_parts.append("Volume alto de finalizações sugere um jogo aberto — boas chances de gol nos dois lados.")
    elif total_shots <= 8 and total_shots > 0:
        radar_parts.append("Poucas finalizações no total indicam um jogo truncado, com defesas bem postadas e espaços escassos.")
    else:
        radar_parts.append("Ritmo moderado — nenhum dos lados conseguiu ainda romper o equilíbrio de forma definitiva.")

    if (h_fouls + a_fouls) > 20:
        radar_parts.append(
            f"Alto volume de faltas ({h_fouls + a_fouls} no total) traz tensão e aumenta o risco de cartões."
        )

    if gap < 10 and best_type != "draw":
        radar_parts.append(
            "Com a margem apertada entre os cenários, uma virada ainda é real — acompanhe o desenvolvimento minuto a minuto."
        )

    if not radar_parts:
        radar_parts.append(random.choice([
            "Tendência de jogo equilibrado, com ambos os times buscando o resultado até o apito final.",
            "Partida de leitura difícil — os primeiros minutos serão determinantes para confirmar a tendência.",
        ]))

    radar_block = "💡 **Radar Elli**\n\n" + " ".join(radar_parts)

    return f"{intro}\n\n{insight_block}\n\n{radar_block}"




# ══════════════════════════════════════════════════════════════════════════════
# PREDIÇÕES
# ══════════════════════════════════════════════════════════════════════════════

def predict_shot(shot_data: dict) -> dict:
    """
    Prediz probabilidade de gol para um chute.

    Args:
        shot_data: dicionário com as features do chute
                   (distance_to_goal, angle_to_goal, xg, technique, ...)

    Returns:
        {
            "goal_probability": float,
            "factors": [...],
            "narrative": str,
            "shap_values": [...],
        }
    """
    artifact = _get_model("goal_model")
    model     = artifact["model"]
    encoders  = artifact["encoders"]
    feat_cols = artifact["feature_cols"]
    explainer = artifact["explainer"]

    # Prepara DataFrame de entrada
    df = pd.DataFrame([shot_data])

    # Encode categoricals usando os encoders do treino
    from src.models.train import encode_categoricals
    df = encode_categoricals(df, artifact["cat_cols"], encoders)

    # Preenche colunas faltantes com 0
    for col in feat_cols:
        if col not in df.columns:
            df[col] = 0

    X = df[feat_cols].astype(float)

    prob = float(model.predict_proba(X)[0, 1])
    shap_vals = explainer.shap_values(X)[0]  # shape (n_features,)

    factors = _top_shap_factors(shap_vals, feat_cols, n=5)
    narrative = _narrative_goal(prob, factors, shot_data)

    return {
        "goal_probability": round(prob, 4),
        "factors": factors,
        "narrative": narrative,
        "shap_values": {feat_cols[i]: round(float(shap_vals[i]), 4) for i in range(len(feat_cols))},
    }


def predict_foul(foul_data: dict) -> dict:
    """Prediz probabilidade de cartão para uma falta."""
    artifact = _get_model("card_model")
    model     = artifact["model"]
    encoders  = artifact["encoders"]
    feat_cols = artifact["feature_cols"]
    explainer = artifact["explainer"]

    df = pd.DataFrame([foul_data])
    from src.models.train import encode_categoricals
    df = encode_categoricals(df, artifact["cat_cols"], encoders)

    for col in feat_cols:
        if col not in df.columns:
            df[col] = 0

    X = df[feat_cols].astype(float)

    prob = float(model.predict_proba(X)[0, 1])
    shap_vals = explainer.shap_values(X)[0]

    factors = _top_shap_factors(shap_vals, feat_cols, n=5)
    narrative = _narrative_card(prob, factors, foul_data)

    return {
        "card_probability": round(prob, 4),
        "factors": factors,
        "narrative": narrative,
        "shap_values": {feat_cols[i]: round(float(shap_vals[i]), 4) for i in range(len(feat_cols))},
    }


def _apply_live_adjustment(
    probs: np.ndarray,
    home_score: int,
    away_score: int,
    minute: int,
) -> np.ndarray:
    """
    Ajusta probabilidades combinando o modelo XGBoost com probabilidades
    empíricas baseadas no placar real e tempo restante.

    Abordagem: BLENDING
    - Calcula probabilidades empíricas usando taxas reais de virada no futebol
    - Calcula peso do placar vs peso do modelo baseado no contexto
    - Quanto maior a diferença de gols E menos tempo resta → mais peso ao placar real
    - Para 0-0 no início → modelo XGBoost prevalece

    Dados empíricos de referência (futebol profissional):
    - Time com 1 gol de vantagem no min 75: ~80% vitória
    - Time com 2 gols no min 75: ~95% vitória  
    - Time com 3+ gols: >98% vitória (independente do minuto)
    - Viradas de 2+ gols acontecem em <3% dos jogos
    """
    goal_diff = home_score - away_score
    abs_diff = abs(goal_diff)
    total_goals = home_score + away_score

    # Clamp minuto
    m = max(0, min(minute, 95))
    time_remaining = max(90 - m, 0)  # minutos restantes

    # ── 1. Calcula probabilidades empíricas baseadas no placar/tempo ──

    if goal_diff == 0:
        # Empate: probabilidade de empate cresce conforme tempo passa
        # No min 0: ~25% empate, min 45: ~30%, min 80: ~50%
        base_draw = 0.25 + 0.30 * (m / 90.0)
        remaining_prob = 1.0 - base_draw
        # Se 0-0, levemente equilibrado; se 2-2, mais empate
        if total_goals > 0:
            base_draw = min(base_draw + 0.05 * total_goals, 0.70)
            remaining_prob = 1.0 - base_draw
        empirical = np.array([remaining_prob * 0.55, base_draw, remaining_prob * 0.45])
    else:
        # Um time vencendo — calcula chance de virada
        # Taxa base: chance do perdedor empatar ou virar cai exponencialmente
        # com a diferença de gols e o tempo decorrido

        # Probabilidade de o líder manter: baseada em dados reais
        if abs_diff >= 3:
            # 3+ gols: praticamente impossível virar
            leader_win = min(0.92 + 0.06 * (m / 90.0), 0.99)
            draw_chance = max(0.01, (1 - leader_win) * 0.3)
            loser_win = max(0.01, 1 - leader_win - draw_chance)
        elif abs_diff == 2:
            # 2 gols: virada muito rara, especialmente depois do min 60
            if time_remaining <= 15:
                leader_win = 0.96
            elif time_remaining <= 30:
                leader_win = 0.92
            elif time_remaining <= 45:
                leader_win = 0.85
            else:
                leader_win = 0.75
            draw_chance = (1 - leader_win) * 0.35
            loser_win = 1 - leader_win - draw_chance
        else:
            # 1 gol: virada possível mas improvável conforme tempo passa
            if time_remaining <= 10:
                leader_win = 0.88
            elif time_remaining <= 20:
                leader_win = 0.78
            elif time_remaining <= 30:
                leader_win = 0.68
            elif time_remaining <= 45:
                leader_win = 0.58
            else:
                leader_win = 0.48
            draw_chance = (1 - leader_win) * 0.45
            loser_win = 1 - leader_win - draw_chance

        # Monta o array na ordem [home_win, draw, away_win]
        if goal_diff > 0:
            empirical = np.array([leader_win, draw_chance, loser_win])
        else:
            empirical = np.array([loser_win, draw_chance, leader_win])

    # ── 2. Calcula peso de cada fonte (modelo vs empírico) ──
    # O peso do placar cresce com:
    #   a) diferença de gols (quanto maior, mais confiável o placar)
    #   b) tempo decorrido (quanto mais tarde, menos muda)
    #   c) total de gols (jogo com gols = mais dados reais)

    time_weight = (m / 90.0) ** 1.5  # 0→1, cresce mais rápido no fim
    score_weight = min(abs_diff * 0.25, 0.75)  # 0, 0.25, 0.50, 0.75
    goal_weight = min(total_goals * 0.08, 0.30)  # até 0.30

    # Peso final do empírico: combinação dos 3 fatores
    empirical_weight = min(time_weight * 0.5 + score_weight + goal_weight, 0.95)

    # Garante mínimo: mesmo no início, se tem 3 gols de diferença, empírico domina
    if abs_diff >= 3:
        empirical_weight = max(empirical_weight, 0.80)
    elif abs_diff >= 2 and m >= 45:
        empirical_weight = max(empirical_weight, 0.65)

    model_weight = 1.0 - empirical_weight

    # ── 3. Blending final ──
    blended = model_weight * probs.astype(float) + empirical_weight * empirical

    # Clamp e normaliza
    blended = np.maximum(blended, 0.01)
    blended /= blended.sum()

    return blended


def predict_match(
    match_data: dict,
    home_team_name: str = "Mandante",
    away_team_name: str = "Visitante",
    home_score: int = 0,
    away_score: int = 0,
    minute: int = 0,
) -> dict:
    """
    Prediz probabilidades de resultado de uma partida.

    Args:
        match_data: features para o modelo XGBoost
        home_team_name: nome do mandante (para narrativa)
        away_team_name: nome do visitante (para narrativa)
        home_score: gols atuais do mandante (para ajuste live)
        away_score: gols atuais do visitante (para ajuste live)
        minute: minuto atual do jogo (para ajuste live)
    """
    artifact  = _get_model("match_model")
    model     = artifact["model"]
    feat_cols = artifact["feature_cols"]
    explainer = artifact["explainer"]

    df = pd.DataFrame([match_data])
    for col in feat_cols:
        if col not in df.columns:
            df[col] = 0

    X = df[feat_cols].astype(float)

    probs_raw = model.predict_proba(X)[0]  # [home_win, draw, away_win]

    # Aplica ajuste live se temos dados de placar/tempo
    if minute > 0 or home_score > 0 or away_score > 0:
        probs = _apply_live_adjustment(probs_raw, home_score, away_score, minute)
    else:
        probs = probs_raw

    shap_vals_all = explainer.shap_values(X)
    dominant_class = int(np.argmax(probs))

    if isinstance(shap_vals_all, list):
        shap_vals = np.array(shap_vals_all[dominant_class]).flatten()[:len(feat_cols)]
    elif isinstance(shap_vals_all, np.ndarray):
        if shap_vals_all.ndim == 3:
            shap_vals = shap_vals_all[0, :, dominant_class]
        elif shap_vals_all.ndim == 2:
            shap_vals = shap_vals_all[0]
        else:
            shap_vals = shap_vals_all.flatten()[:len(feat_cols)]
    else:
        shap_vals = np.zeros(len(feat_cols))

    factors = _top_shap_factors(shap_vals, feat_cols, n=5)
    narrative = _narrative_match(
        probs, factors,
        home_name=home_team_name,
        away_name=away_team_name,
        match_stats=match_data,
    )

    return {
        "home_win_probability":  round(float(probs[0]), 4),
        "draw_probability":      round(float(probs[1]), 4),
        "away_win_probability":  round(float(probs[2]), 4),
        "dominant_outcome":      artifact["class_names"][dominant_class],
        "factors":               factors,
        "narrative":             narrative,
        "home_team_name":        home_team_name,
        "away_team_name":        away_team_name,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SIMULAÇÃO — MOTOR "E SE?"
# ══════════════════════════════════════════════════════════════════════════════

def simulate_what_if(
    prediction_type: str,
    base_data: dict,
    overrides: dict,
    description: str = "",
) -> dict:
    """
    Simula um cenário hipotético alterando features da predição base.

    Args:
        prediction_type: "shot" | "foul" | "match"
        base_data: features do cenário real
        overrides: features a alterar (e.g. {"distance_to_goal": 10, "under_pressure": 0})
        description: texto livre do cenário (e.g. "E se o chute fosse mais perto?")

    Returns:
        {
            "base": {...predição original...},
            "simulated": {...predição com alterações...},
            "delta": {metric: simulated - base},
            "narrative": str,
        }
    """
    impact_pct_change = None

    def _call_match_with_live(dt_dict: dict) -> dict:
        return predict_match(
            match_data=dt_dict,
            home_score=dt_dict.get("home_score", 0),
            away_score=dt_dict.get("away_score", 0),
            minute=dt_dict.get("minute", 60)
        )

    if prediction_type == "shot":
        base_result = predict_shot(base_data)
        sim_data = {**base_data, **overrides}
        sim_result = predict_shot(sim_data)
        base_prob  = base_result["goal_probability"]
        sim_prob   = sim_result["goal_probability"]
        metric_key = "goal_probability"
        
        # Cascata de Impacto na Vitória
        base_match = _call_match_with_live(base_data)
        is_home = overrides.get("is_home_team", 1)
        sim_match_data = base_data.copy()
        
        if is_home:
            sim_match_data["home_score"] = sim_match_data.get("home_score", 0) + 1
        else:
            sim_match_data["away_score"] = sim_match_data.get("away_score", 0) + 1
        
        sim_match = _call_match_with_live(sim_match_data)
        impact_delta = (sim_match["home_win_probability"] - base_match["home_win_probability"]) if is_home else (sim_match["away_win_probability"] - base_match["away_win_probability"])
        impact_pct_change = round(impact_delta * 100, 1)

    elif prediction_type == "foul":
        base_result = predict_foul(base_data)
        sim_data = {**base_data, **overrides}
        sim_result = predict_foul(sim_data)
        base_prob  = base_result["card_probability"]
        sim_prob   = sim_result["card_probability"]
        metric_key = "card_probability"

        # Cascata de Impacto (Penalidade técnica e de controle ou expulsao)
        base_match = _call_match_with_live(base_data)
        is_home = overrides.get("is_home_team", 1)
        sim_match_data = base_data.copy()
        if is_home:
            sim_match_data["home_fouls"] = sim_match_data.get("home_fouls", 0) + 1
            sim_match_data["pressure_ratio"] = max(0.1, sim_match_data.get("pressure_ratio", 1.0) - 0.2)
        else:
            sim_match_data["away_fouls"] = sim_match_data.get("away_fouls", 0) + 1
            sim_match_data["pressure_ratio"] = min(3.0, sim_match_data.get("pressure_ratio", 1.0) + 0.2)

        sim_match = _call_match_with_live(sim_match_data)
        impact_delta = (sim_match["home_win_probability"] - base_match["home_win_probability"]) if is_home else (sim_match["away_win_probability"] - base_match["away_win_probability"])
        impact_pct_change = round(impact_delta * 100, 1)

    elif prediction_type == "match":
        base_result = _call_match_with_live(base_data)
        sim_data = {**base_data, **overrides}
        sim_result = _call_match_with_live(sim_data)
        
        is_home = overrides.get("is_home_team", 1)
        base_prob  = base_result["home_win_probability"] if is_home else base_result["away_win_probability"]
        sim_prob   = sim_result["home_win_probability"] if is_home else sim_result["away_win_probability"]
        metric_key = "team_win_probability"

    else:
        raise ValueError(f"prediction_type inválido: {prediction_type}")

    delta = round(sim_prob - base_prob, 4)
    pct_change = round(delta * 100, 1)

    narrative = generate_simulation_narrative(
        prediction_type=prediction_type,
        description=description,
        changes=overrides,
        pct_change=pct_change,
        impact_pct_change=impact_pct_change
    )

    return {
        "base": base_result,
        "simulated": sim_result,
        "delta": {metric_key: delta},
        "description": description,
        "narrative": narrative,
    }
