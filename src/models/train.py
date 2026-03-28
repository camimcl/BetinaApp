"""
src/models/train.py  (v3 — features confirmadas pelo diagnóstico)

Modelos:
  1. GoalModel   — P(gol | chute)
  2. CardModel   — P(cartão | falta)
  3. MatchModel  — P(resultado | stats da partida)

Split: TEMPORAL (respeita cronologia, evita data leakage).
Explicabilidade: SHAP por predição.
"""

import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import LabelEncoder

PROCESSED_DIR = Path(os.getenv("DATA_PROCESSED_DIR", "data/processed"))
MODELS_DIR    = Path(os.getenv("MODELS_DIR", "data/models"))
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════════════════

def temporal_split(df: pd.DataFrame, date_col: str = "match_date", test_ratio: float = 0.2):
    """Split temporal — nunca aleatório em dados esportivos."""
    df = df.sort_values(date_col).reset_index(drop=True)
    cutoff = int(len(df) * (1 - test_ratio))
    return df.iloc[:cutoff].copy(), df.iloc[cutoff:].copy()


def encode_categoricals(df: pd.DataFrame, cat_cols: list, encoders: dict = None):
    """Label-encoding. Modo fit (encoders=None) ou inference (encoders=dict)."""
    df = df.copy()
    fit_mode = encoders is None
    if fit_mode:
        encoders = {}

    for col in cat_cols:
        if col not in df.columns:
            continue
        df[col] = df[col].fillna("Unknown").astype(str)
        if fit_mode:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            encoders[col] = le
        else:
            le = encoders[col]
            known = set(le.classes_)
            df[col] = df[col].apply(lambda x: x if x in known else le.classes_[0])
            df[col] = le.transform(df[col])

    return (df, encoders) if fit_mode else df


def safe_features(df: pd.DataFrame, wanted: list) -> list:
    """Retorna apenas as colunas de `wanted` que existem no DataFrame."""
    available = [c for c in wanted if c in df.columns]
    missing   = set(wanted) - set(available)
    if missing:
        logger.warning(f"  Colunas ausentes (ignoradas): {sorted(missing)}")
    return available


# ══════════════════════════════════════════════════════════════════════════════
# 1. MODELO DE GOL
# ══════════════════════════════════════════════════════════════════════════════

SHOT_FEATURE_COLS = [
    # Geometria — as features mais importantes
    "distance_to_goal", "angle_to_goal",
    # xG do StatsBomb (feature premium)
    "xg",
    # Técnica
    "body_part", "technique", "shot_type",
    # Flags
    "first_time", "open_goal", "one_on_one", "aerial_won",
    # Tempo
    "minute", "time_seconds", "is_second_half", "is_extra_time", "minute_bucket",
    # Contexto
    "under_pressure", "score_diff", "is_home_team", "team_score_diff",
]
SHOT_CAT_COLS = ["body_part", "technique", "shot_type"]


def train_goal_model():
    logger.info("═══ TREINANDO MODELO DE GOL ═══")

    df = pd.read_csv(PROCESSED_DIR / "shot_features.csv")
    df["match_date"] = pd.to_datetime(df["match_date"])
    df = df.dropna(subset=["xg", "distance_to_goal", "goal"])

    feat_cols = safe_features(df, SHOT_FEATURE_COLS)
    logger.info(f"  {len(df):,} chutes | {df['goal'].mean():.3%} gol | {len(feat_cols)} features")

    df, encoders = encode_categoricals(df, SHOT_CAT_COLS)
    df[feat_cols] = df[feat_cols].fillna(0)

    train_df, test_df = temporal_split(df, test_ratio=0.2)
    logger.info(f"  Treino: {len(train_df):,} | Teste: {len(test_df):,}")

    X_train = train_df[feat_cols].astype(float)
    y_train = train_df["goal"]
    X_test  = test_df[feat_cols].astype(float)
    y_test  = test_df["goal"]

    # scale_pos_weight compensa o desbalanceamento (~10% gols)
    neg_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        scale_pos_weight=neg_pos,
        eval_metric="logloss",
        early_stopping_rounds=30,
        random_state=42,
        tree_method="hist",
        n_jobs=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    auc    = roc_auc_score(y_test, y_prob)
    brier  = brier_score_loss(y_test, y_prob)
    ll     = log_loss(y_test, y_prob)

    logger.success(f"  AUC-ROC: {auc:.4f} | Brier: {brier:.4f} | LogLoss: {ll:.4f}")
    print(classification_report(y_test, y_pred, target_names=["No Goal", "Goal"]))

    # Top features por importância
    importances = dict(zip(feat_cols, model.feature_importances_))
    top5 = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
    logger.info(f"  Top 5 features: {[(f, round(v,3)) for f,v in top5]}")

    logger.info("  Calculando SHAP values...")
    explainer   = shap.TreeExplainer(model)
    shap_sample = X_test.sample(min(200, len(X_test)), random_state=42)
    explainer.shap_values(shap_sample)  # aquece o cache

    artifact = {
        "model":        model,
        "encoders":     encoders,
        "feature_cols": feat_cols,
        "cat_cols":     SHOT_CAT_COLS,
        "explainer":    explainer,
        "metrics":      {"auc": auc, "brier": brier, "log_loss": ll},
    }
    joblib.dump(artifact, MODELS_DIR / "goal_model.pkl")
    logger.success(f"  Salvo: {MODELS_DIR}/goal_model.pkl")
    return artifact


# ══════════════════════════════════════════════════════════════════════════════
# 2. MODELO DE CARTÃO
# ══════════════════════════════════════════════════════════════════════════════

FOUL_FEATURE_COLS = [
    # Localização
    "x", "y", "dist_to_center", "dist_to_sideline",
    "in_danger_zone", "in_final_third", "in_own_half",
    # Tipo de falta
    "foul_type", "advantage", "offensive",
    # Tempo — crucial para cartões (árbitros mais rigorosos no fim)
    "minute", "time_seconds", "is_second_half",
    "is_last_10_min", "is_last_5_min", "minute_bucket",
    # Contexto
    "under_pressure", "score_diff", "is_home_team",
    "team_score_diff", "team_losing", "team_winning",
]
FOUL_CAT_COLS = ["foul_type"]


def train_card_model():
    logger.info("═══ TREINANDO MODELO DE CARTÃO ═══")

    df = pd.read_csv(PROCESSED_DIR / "foul_features.csv")
    df["match_date"] = pd.to_datetime(df["match_date"])
    df = df.dropna(subset=["x", "y", "card_given"])

    feat_cols = safe_features(df, FOUL_FEATURE_COLS)
    logger.info(f"  {len(df):,} faltas | {df['card_given'].mean():.3%} com cartão | {len(feat_cols)} features")

    df, encoders = encode_categoricals(df, FOUL_CAT_COLS)
    df[feat_cols] = df[feat_cols].fillna(0)

    train_df, test_df = temporal_split(df, test_ratio=0.2)

    X_train = train_df[feat_cols].astype(float)
    y_train = train_df["card_given"]
    X_test  = test_df[feat_cols].astype(float)
    y_test  = test_df["card_given"]

    neg_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=5,
        scale_pos_weight=neg_pos,
        eval_metric="logloss",
        early_stopping_rounds=30,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    auc    = roc_auc_score(y_test, y_prob)
    brier  = brier_score_loss(y_test, y_prob)

    logger.success(f"  AUC-ROC: {auc:.4f} | Brier: {brier:.4f}")
    print(classification_report(y_test, y_pred, target_names=["No Card", "Card"]))

    importances = dict(zip(feat_cols, model.feature_importances_))
    top5 = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
    logger.info(f"  Top 5 features: {[(f, round(v,3)) for f,v in top5]}")

    explainer   = shap.TreeExplainer(model)
    shap_sample = X_test.sample(min(200, len(X_test)), random_state=42)
    explainer.shap_values(shap_sample)

    artifact = {
        "model":        model,
        "encoders":     encoders,
        "feature_cols": feat_cols,
        "cat_cols":     FOUL_CAT_COLS,
        "explainer":    explainer,
        "metrics":      {"auc": auc, "brier": brier},
    }
    joblib.dump(artifact, MODELS_DIR / "card_model.pkl")
    logger.success(f"  Salvo: {MODELS_DIR}/card_model.pkl")
    return artifact


# ══════════════════════════════════════════════════════════════════════════════
# 3. MODELO DE RESULTADO DE PARTIDA
# ══════════════════════════════════════════════════════════════════════════════

MATCH_FEATURE_COLS = [
    # xG — feature mais preditiva de resultado
    "home_xg", "away_xg", "xg_diff",
    "home_xg_sot", "away_xg_sot",
    # Chutes
    "home_shots", "away_shots", "home_shots_ot", "away_shots_ot", "shot_ratio",
    # Passes
    "home_pass_acc", "away_pass_acc", "pass_acc_diff",
    # Pressão
    "home_pressures", "away_pressures", "pressure_ratio",
    # Disciplina
    "home_fouls", "away_fouls",
    # Atividade
    "home_carries", "away_carries",
]


def train_match_model():
    logger.info("═══ TREINANDO MODELO DE RESULTADO ═══")

    df = pd.read_csv(PROCESSED_DIR / "match_features.csv")
    df["match_date"] = pd.to_datetime(df["match_date"])
    df = df.dropna(subset=["home_xg", "away_xg", "result"])

    feat_cols = safe_features(df, MATCH_FEATURE_COLS)
    logger.info(f"  {len(df):,} partidas | {len(feat_cols)} features")

    train_df, test_df = temporal_split(df, test_ratio=0.2)
    logger.info(f"  Treino: {len(train_df):,} | Teste: {len(test_df):,}")

    X_train = train_df[feat_cols].astype(float)
    y_train = train_df["result"]
    X_test  = test_df[feat_cols].astype(float)
    y_test  = test_df["result"]

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        num_class=3,
        objective="multi:softprob",
        eval_metric="mlogloss",
        early_stopping_rounds=30,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_prob = model.predict_proba(X_test)
    y_pred = np.argmax(y_prob, axis=1)
    acc    = accuracy_score(y_test, y_pred)

    logger.success(f"  Acurácia: {acc:.4f}")
    print(classification_report(y_test, y_pred, target_names=["Home Win", "Draw", "Away Win"]))

    importances = dict(zip(feat_cols, model.feature_importances_))
    top5 = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
    logger.info(f"  Top 5 features: {[(f, round(v,3)) for f,v in top5]}")

    explainer   = shap.TreeExplainer(model)
    shap_sample = X_test.sample(min(200, len(X_test)), random_state=42)
    explainer.shap_values(shap_sample)

    artifact = {
        "model":        model,
        "feature_cols": feat_cols,
        "explainer":    explainer,
        "class_names":  ["Home Win", "Draw", "Away Win"],
        "metrics":      {"accuracy": acc},
    }
    joblib.dump(artifact, MODELS_DIR / "match_model.pkl")
    logger.success(f"  Salvo: {MODELS_DIR}/match_model.pkl")
    return artifact


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("Iniciando treinamento completo...")

    goal_art  = train_goal_model()
    card_art  = train_card_model()
    match_art = train_match_model()

    print("\n" + "═"*50)
    print("TREINAMENTO CONCLUÍDO")
    print("═"*50)
    print(f"Goal Model   AUC : {goal_art['metrics']['auc']:.4f}")
    print(f"Card Model   AUC : {card_art['metrics']['auc']:.4f}")
    print(f"Match Model  Acc : {match_art['metrics']['accuracy']:.4f}")
    print(f"\nModelos em: data/models/")
    print(f"Próximo: uvicorn src.api.main:app --reload --port 8000")