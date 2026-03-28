"""
src/data/feature_builder.py  (v3 — IDs e colunas confirmados pelo explore_statsbomb.py)

Colunas confirmadas pelo diagnóstico:
  CHUTE : shot_statsbomb_xg, shot_body_part, shot_outcome, shot_technique,
          shot_type, shot_first_time, shot_open_goal, shot_one_on_one
  FALTA : foul_committed_card, foul_committed_type, foul_committed_advantage,
          foul_committed_offensive  (sem sufixo _name)

IDs corrigidos:
  La Liga 2020/21  → competition_id=11, season_id=90
  La Liga 2019/20  → competition_id=11, season_id=42
  La Liga 2015/16  → competition_id=11, season_id=27   ← era 90 antes (errado)
  Premier League 2003/04 → competition_id=2,  season_id=44
  Champions League 2018/19 → competition_id=16, season_id=4
  FIFA World Cup 2022 → competition_id=43, season_id=106
  FIFA World Cup 2018 → competition_id=43, season_id=3
  UEFA Euro 2020   → competition_id=55, season_id=43  ← era 16/4 antes (errado)
  UEFA Euro 2024   → competition_id=55, season_id=282
"""

import os
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from loguru import logger
from statsbombpy import sb
from tqdm import tqdm

# ── Competições (IDs verificados pelo explore_statsbomb.py) ──────────────────
# Escolhemos volume + qualidade de dados.
# La Liga tem a maior cobertura histórica do StatsBomb Open Data.
COMPETITIONS = [
    # (competition_id, season_id, label)
    (11,  90,  "La Liga 2020/21"),
    (11,  42,  "La Liga 2019/20"),
    (11,  27,  "La Liga 2015/16"),
    (11,   4,  "La Liga 2018/19"),
    (11,   1,  "La Liga 2017/18"),
    (11,   2,  "La Liga 2016/17"),
    (2,   44,  "Premier League 2003/04"),
    (43, 106,  "FIFA World Cup 2022"),
    (43,   3,  "FIFA World Cup 2018"),
    (55,  43,  "UEFA Euro 2020"),
    (16,   4,  "Champions League 2018/19"),
]

PROCESSED_DIR = Path(os.getenv("DATA_PROCESSED_DIR", "data/processed"))
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _parse_xy(loc) -> Tuple[float, float]:
    """Extrai (x, y) de location que pode ser lista, tuple ou string."""
    if loc is None or (isinstance(loc, float) and np.isnan(loc)):
        return np.nan, np.nan
    if isinstance(loc, (list, tuple)) and len(loc) >= 2:
        return float(loc[0]), float(loc[1])
    if isinstance(loc, str):
        try:
            import ast
            loc = ast.literal_eval(loc)
            if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                return float(loc[0]), float(loc[1])
        except Exception:
            pass
    return np.nan, np.nan


def _distance_to_goal(x: float, y: float) -> float:
    """Campo StatsBomb 120×80. Centro do gol em (120, 40)."""
    return float(np.sqrt((120 - x) ** 2 + (40 - y) ** 2))


def _angle_to_goal(x: float, y: float) -> float:
    """
    Ângulo (graus) entre os postes (120,36) e (120,44) visto de (x,y).
    Quanto maior, mais fácil o chute.
    """
    p1 = np.array([120, 36]) - np.array([x, y])
    p2 = np.array([120, 44]) - np.array([x, y])
    denom = np.linalg.norm(p1) * np.linalg.norm(p2) + 1e-9
    cos_a = np.dot(p1, p2) / denom
    return float(np.degrees(np.arccos(np.clip(cos_a, -1, 1))))


def _resolve_col(df: pd.DataFrame, candidates: list, default=np.nan) -> pd.Series:
    """Retorna a primeira coluna que existir. Loga quais foram tentadas."""
    for c in candidates:
        if c in df.columns:
            return df[c]
    logger.debug(f"  Nenhuma coluna encontrada em: {candidates} — usando default={default}")
    return pd.Series([default] * len(df), index=df.index)


# ══════════════════════════════════════════════════════════════════════════════
# 1. CARREGAMENTO
# ══════════════════════════════════════════════════════════════════════════════

def load_all_events() -> pd.DataFrame:
    """
    Baixa todos os eventos de todas as competições configuradas.
    O statsbombpy já faz o flatten das colunas aninhadas automaticamente.
    """
    all_events = []

    for comp_id, season_id, label in COMPETITIONS:
        logger.info(f"Carregando {label} (comp={comp_id}, season={season_id})...")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            logger.warning(f"  Falha ao carregar partidas de {label}: {e}")
            continue

        logger.info(f"  {len(matches)} partidas encontradas")

        for _, match_row in tqdm(matches.iterrows(), total=len(matches), desc=label, leave=False):
            match_id = match_row["match_id"]
            try:
                events = sb.events(match_id=match_id)
                events["match_id"]          = match_id
                events["competition_label"] = label
                events["competition_id"]    = comp_id
                events["season_id"]         = season_id
                events["match_date"]        = match_row["match_date"]
                events["home_team"]         = match_row["home_team"]
                events["away_team"]         = match_row["away_team"]
                events["home_score"]        = match_row["home_score"]
                events["away_score"]        = match_row["away_score"]
                all_events.append(events)
            except Exception as e:
                logger.warning(f"  Falha na partida {match_id}: {e}")

    if not all_events:
        raise RuntimeError("Nenhum evento carregado. Verifique os IDs de competição.")

    df = pd.concat(all_events, ignore_index=True)
    logger.success(f"Total de eventos: {len(df):,} em {df['match_id'].nunique()} partidas")

    # Diagnóstico rápido de colunas (ajuda a detectar mudanças na API)
    shot_cols = sorted([c for c in df.columns if "shot" in c.lower()])
    foul_cols = sorted([c for c in df.columns if "foul" in c.lower()])
    logger.debug(f"  Colunas shot: {shot_cols}")
    logger.debug(f"  Colunas foul: {foul_cols}")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 2. FEATURES DE CHUTE
# ══════════════════════════════════════════════════════════════════════════════
# Colunas confirmadas pelo diagnóstico:
#   shot_statsbomb_xg, shot_body_part, shot_outcome, shot_technique,
#   shot_type, shot_first_time, shot_open_goal, shot_one_on_one

def build_shot_features(events: pd.DataFrame) -> pd.DataFrame:
    logger.info("Construindo features de chutes...")
    shots = events[events["type"] == "Shot"].copy()
    logger.info(f"  {len(shots):,} chutes brutos")

    if len(shots) == 0:
        raise ValueError("Nenhum evento Shot encontrado.")

    # ── Localização e geometria ───────────────────────────────────────────────
    xy = shots["location"].apply(_parse_xy)
    shots["x"] = xy.apply(lambda t: t[0])
    shots["y"] = xy.apply(lambda t: t[1])

    mask = shots["x"].notna() & shots["y"].notna()
    shots.loc[mask, "distance_to_goal"] = shots.loc[mask].apply(
        lambda r: _distance_to_goal(r["x"], r["y"]), axis=1
    )
    shots.loc[mask, "angle_to_goal"] = shots.loc[mask].apply(
        lambda r: _angle_to_goal(r["x"], r["y"]), axis=1
    )

    # ── xG do StatsBomb ───────────────────────────────────────────────────────
    # Coluna confirmada: shot_statsbomb_xg
    shots["xg"] = pd.to_numeric(
        _resolve_col(shots, ["shot_statsbomb_xg"]), errors="coerce"
    )

    # ── Atributos do chute ────────────────────────────────────────────────────
    # Confirmados pelo diagnóstico: sem sufixo _name, valores são strings diretas
    shots["body_part"]        = _resolve_col(shots, ["shot_body_part"], "Right Foot").fillna("Right Foot")
    shots["technique"]        = _resolve_col(shots, ["shot_technique"], "Normal").fillna("Normal")
    shots["shot_type"]        = _resolve_col(shots, ["shot_type"], "Open Play").fillna("Open Play")
    shots["outcome_raw"]      = _resolve_col(shots, ["shot_outcome"], "").fillna("")

    # Flags booleanas
    shots["first_time"]       = _resolve_col(shots, ["shot_first_time"],  False).fillna(False).astype(int)
    shots["open_goal"]        = _resolve_col(shots, ["shot_open_goal"],   False).fillna(False).astype(int)
    shots["one_on_one"]       = _resolve_col(shots, ["shot_one_on_one"],  False).fillna(False).astype(int)
    shots["aerial_won"]       = _resolve_col(shots, ["shot_aerial_won"],  False).fillna(False).astype(int)

    # ── Contexto temporal ─────────────────────────────────────────────────────
    shots["minute"]           = pd.to_numeric(shots["minute"], errors="coerce").fillna(0)
    shots["second"]           = pd.to_numeric(shots.get("second", pd.Series(0, index=shots.index)), errors="coerce").fillna(0)
    shots["time_seconds"]     = shots["minute"] * 60 + shots["second"]
    shots["is_second_half"]   = (shots["minute"] >= 45).astype(int)
    shots["is_extra_time"]    = (shots["minute"] >= 90).astype(int)
    shots["minute_bucket"]    = (shots["minute"] // 15).astype(int)  # 0-6, captura curva de gol por período

    # ── Pressão e contexto tático ─────────────────────────────────────────────
    shots["under_pressure"]   = shots["under_pressure"].fillna(False).astype(int) if "under_pressure" in shots.columns else 0

    # ── Placar no momento do chute ────────────────────────────────────────────
    shots["home_score"]       = pd.to_numeric(shots["home_score"], errors="coerce").fillna(0)
    shots["away_score"]       = pd.to_numeric(shots["away_score"], errors="coerce").fillna(0)
    shots["score_diff"]       = shots["home_score"] - shots["away_score"]
    shots["is_home_team"]     = (shots["team"] == shots["home_team"]).astype(int)
    # Perspectiva do atacante: positivo = liderando, negativo = perdendo
    shots["team_score_diff"]  = shots.apply(
        lambda r: r["score_diff"] if r["is_home_team"] else -r["score_diff"], axis=1
    )

    # ── Target ───────────────────────────────────────────────────────────────
    # outcome_raw confirmado: "Goal", "Off T", "Saved", "Blocked", "Post", etc.
    shots["goal"] = shots["outcome_raw"].str.strip().str.lower().eq("goal").astype(int)

    n_goals = shots["goal"].sum()
    logger.success(f"  Gols: {n_goals:,} / {len(shots):,} chutes = {shots['goal'].mean():.3%}")

    # ── Seleção final de colunas ──────────────────────────────────────────────
    feat_cols = [
        "match_id", "competition_label", "match_date",
        # Geometria
        "x", "y", "distance_to_goal", "angle_to_goal",
        # xG
        "xg",
        # Técnica
        "body_part", "technique", "shot_type",
        "first_time", "open_goal", "one_on_one", "aerial_won",
        # Tempo
        "minute", "time_seconds", "is_second_half", "is_extra_time", "minute_bucket",
        # Contexto
        "under_pressure", "score_diff", "is_home_team", "team_score_diff",
        # Target
        "goal",
    ]
    shots = shots[[c for c in feat_cols if c in shots.columns]]
    shots = shots.dropna(subset=["x", "y", "xg"])

    logger.success(f"  Após limpeza: {len(shots):,} chutes com features completas")
    return shots


# ══════════════════════════════════════════════════════════════════════════════
# 3. FEATURES DE FALTA
# ══════════════════════════════════════════════════════════════════════════════
# Colunas confirmadas: foul_committed_card, foul_committed_type,
#                      foul_committed_advantage, foul_committed_offensive
# IMPORTANTE: os valores SÃO dicionários {"id":..., "name":...}
# Precisamos extrair o campo "name" de cada um

def _extract_name(val, default="") -> str:
    """Extrai o campo 'name' de um valor que pode ser dict, string ou NaN."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    if isinstance(val, dict):
        return val.get("name", default)
    if isinstance(val, str):
        # Às vezes vem como string do tipo "{'id': 1, 'name': 'Regular'}"
        try:
            import ast
            d = ast.literal_eval(val)
            if isinstance(d, dict):
                return d.get("name", default)
        except Exception:
            pass
        return val  # já é string simples
    return default


def build_foul_features(events: pd.DataFrame) -> pd.DataFrame:
    logger.info("Construindo features de faltas...")
    fouls = events[events["type"] == "Foul Committed"].copy()
    logger.info(f"  {len(fouls):,} faltas brutas")

    if len(fouls) == 0:
        raise ValueError("Nenhum evento Foul Committed encontrado.")

    # Debug: mostra valores reais para validar _extract_name
    sample_card = fouls["foul_committed_card"].dropna().iloc[0] if "foul_committed_card" in fouls.columns and fouls["foul_committed_card"].notna().any() else None
    sample_type = fouls["foul_committed_type"].dropna().iloc[0] if "foul_committed_type" in fouls.columns and fouls["foul_committed_type"].notna().any() else None
    logger.info(f"  Exemplo foul_committed_card: {sample_card}")
    logger.info(f"  Exemplo foul_committed_type: {sample_type}")

    # ── Localização ──────────────────────────────────────────────────────────
    xy = fouls["location"].apply(_parse_xy)
    fouls["x"] = xy.apply(lambda t: t[0])
    fouls["y"] = xy.apply(lambda t: t[1])

    mask = fouls["x"].notna() & fouls["y"].notna()
    fouls.loc[mask, "dist_to_center"] = fouls.loc[mask].apply(
        lambda r: float(np.sqrt((r["x"] - 60) ** 2 + (r["y"] - 40) ** 2)), axis=1
    )

    # Zonas do campo
    fouls["in_danger_zone"]   = (fouls["x"].fillna(0) > 90).astype(int)   # área adversária
    fouls["in_final_third"]   = (fouls["x"].fillna(0) > 80).astype(int)   # último terço
    fouls["in_own_half"]      = (fouls["x"].fillna(60) < 60).astype(int)  # próprio campo

    # Distância da linha lateral (centro = y=40)
    fouls["dist_to_sideline"] = fouls["y"].fillna(40).apply(lambda y: min(y, 80 - y))

    # ── Tipo de falta (dict com "name") ───────────────────────────────────────
    if "foul_committed_type" in fouls.columns:
        fouls["foul_type"] = fouls["foul_committed_type"].apply(
            lambda v: _extract_name(v, "Regular")
        )
    else:
        fouls["foul_type"] = "Regular"

    # ── Flags ─────────────────────────────────────────────────────────────────
    for col, feat_name, default in [
        ("foul_committed_advantage", "advantage", False),
        ("foul_committed_offensive", "offensive", False),
    ]:
        if col in fouls.columns:
            fouls[feat_name] = fouls[col].fillna(default).astype(bool).astype(int)
        else:
            fouls[feat_name] = 0

    # ── Target: cartão dado? ──────────────────────────────────────────────────
    # foul_committed_card é dict {"id":..., "name": "Yellow Card" | "Red Card" | ...}
    if "foul_committed_card" in fouls.columns:
        fouls["card_name"] = fouls["foul_committed_card"].apply(
            lambda v: _extract_name(v, "")
        )
    else:
        fouls["card_name"] = ""
        logger.warning("  Coluna foul_committed_card não encontrada!")

    fouls["card_given"]       = fouls["card_name"].str.contains("Yellow|Red", case=False, na=False).astype(int)
    fouls["yellow_card"]      = fouls["card_name"].str.contains("Yellow", case=False, na=False).astype(int)
    fouls["red_card"]         = fouls["card_name"].str.contains("Red", case=False, na=False).astype(int)

    n_cards = fouls["card_given"].sum()
    logger.success(f"  Cartões: {n_cards:,} / {len(fouls):,} faltas = {fouls['card_given'].mean():.3%}")
    logger.info(f"  Amarelos: {fouls['yellow_card'].sum():,} | Vermelhos: {fouls['red_card'].sum():,}")

    # ── Contexto temporal ─────────────────────────────────────────────────────
    fouls["minute"]           = pd.to_numeric(fouls["minute"], errors="coerce").fillna(0)
    fouls["second"]           = pd.to_numeric(fouls.get("second", pd.Series(0, index=fouls.index)), errors="coerce").fillna(0)
    fouls["time_seconds"]     = fouls["minute"] * 60 + fouls["second"]
    fouls["is_second_half"]   = (fouls["minute"] >= 45).astype(int)
    fouls["is_last_10_min"]   = (fouls["minute"] >= 80).astype(int)
    fouls["is_last_5_min"]    = (fouls["minute"] >= 85).astype(int)
    fouls["minute_bucket"]    = (fouls["minute"] // 15).astype(int)

    # ── Pressão e placar ──────────────────────────────────────────────────────
    fouls["under_pressure"]   = fouls["under_pressure"].fillna(False).astype(int) if "under_pressure" in fouls.columns else 0
    fouls["home_score"]       = pd.to_numeric(fouls["home_score"], errors="coerce").fillna(0)
    fouls["away_score"]       = pd.to_numeric(fouls["away_score"], errors="coerce").fillna(0)
    fouls["score_diff"]       = fouls["home_score"] - fouls["away_score"]
    fouls["is_home_team"]     = (fouls["team"] == fouls["home_team"]).astype(int)
    fouls["team_score_diff"]  = fouls.apply(
        lambda r: r["score_diff"] if r["is_home_team"] else -r["score_diff"], axis=1
    )
    # Time perdendo = mais propenso a faltas duras
    fouls["team_losing"]      = (fouls["team_score_diff"] < 0).astype(int)
    fouls["team_winning"]     = (fouls["team_score_diff"] > 0).astype(int)

    # ── Seleção final ─────────────────────────────────────────────────────────
    feat_cols = [
        "match_id", "competition_label", "match_date",
        # Localização
        "x", "y", "dist_to_center", "dist_to_sideline",
        "in_danger_zone", "in_final_third", "in_own_half",
        # Tipo de falta
        "foul_type", "advantage", "offensive",
        # Tempo
        "minute", "time_seconds", "is_second_half",
        "is_last_10_min", "is_last_5_min", "minute_bucket",
        # Contexto
        "under_pressure", "score_diff", "is_home_team",
        "team_score_diff", "team_losing", "team_winning",
        # Targets
        "card_given", "yellow_card", "red_card",
    ]
    fouls = fouls[[c for c in feat_cols if c in fouls.columns]]
    fouls = fouls.dropna(subset=["x", "y"])

    logger.success(f"  Após limpeza: {len(fouls):,} faltas com features completas")
    return fouls


# ══════════════════════════════════════════════════════════════════════════════
# 4. FEATURES DE PARTIDA
# ══════════════════════════════════════════════════════════════════════════════

def _aggregate_team(events: pd.DataFrame, match_id: int, team: str) -> dict:
    """Agrega estatísticas de um time em uma partida específica."""
    m = events[events["match_id"] == match_id]
    t = m[m["team"] == team]

    shots   = t[t["type"] == "Shot"]
    passes  = t[t["type"] == "Pass"]
    press   = t[t["type"] == "Pressure"]
    fouls   = t[t["type"] == "Foul Committed"]
    carries = t[t["type"] == "Carry"]
    duels   = t[t["type"] == "Duel"]

    # xG total
    xg_col = "shot_statsbomb_xg" if "shot_statsbomb_xg" in shots.columns else None
    xg_total = float(pd.to_numeric(shots[xg_col], errors="coerce").sum()) if xg_col and len(shots) else 0.0

    # xG de chutes no alvo
    sot_outcomes = {"Goal", "Saved", "Saved To Post", "Saved Off Post", "goal", "saved"}
    out_col = "shot_outcome" if "shot_outcome" in shots.columns else None
    if out_col and len(shots):
        sot_mask  = shots[out_col].apply(lambda v: _extract_name(v, "") if isinstance(v, dict) else str(v) if pd.notna(v) else "").isin(sot_outcomes)
        shots_ot  = int(sot_mask.sum())
        xg_sot    = float(pd.to_numeric(shots.loc[sot_mask, xg_col], errors="coerce").sum()) if xg_col else 0.0
    else:
        shots_ot, xg_sot = 0, 0.0

    # Passes completos (sem outcome = completo no StatsBomb)
    pass_out_col = next((c for c in ["pass_outcome_name", "pass_outcome"] if c in passes.columns), None)
    passes_completed = int(passes[pass_out_col].isna().sum()) if pass_out_col and len(passes) else len(passes)

    return {
        "shots":            len(shots),
        "shots_ot":         shots_ot,
        "xg_total":         xg_total,
        "xg_sot":           xg_sot,
        "passes":           len(passes),
        "pass_acc":         passes_completed / max(len(passes), 1),
        "pressures":        len(press),
        "fouls":            len(fouls),
        "carries":          len(carries),
        "duels":            len(duels),
    }


def build_match_features(events: pd.DataFrame) -> pd.DataFrame:
    logger.info("Construindo features de partidas...")

    match_info = (
        events.drop_duplicates("match_id")
        [["match_id", "competition_label", "match_date",
          "home_team", "away_team", "home_score", "away_score"]]
        .copy()
    )

    rows = []
    for _, mi in tqdm(match_info.iterrows(), total=len(match_info), desc="Agregando partidas"):
        mid  = mi["match_id"]
        home = _aggregate_team(events, mid, mi["home_team"])
        away = _aggregate_team(events, mid, mi["away_team"])
        hs   = int(pd.to_numeric(mi["home_score"], errors="coerce") or 0)
        as_  = int(pd.to_numeric(mi["away_score"], errors="coerce") or 0)

        rows.append({
            "match_id":          mid,
            "competition_label": mi["competition_label"],
            "match_date":        mi["match_date"],
            # xG
            "home_xg":           home["xg_total"],
            "away_xg":           away["xg_total"],
            "xg_diff":           home["xg_total"] - away["xg_total"],
            "home_xg_sot":       home["xg_sot"],
            "away_xg_sot":       away["xg_sot"],
            # Chutes
            "home_shots":        home["shots"],
            "away_shots":        away["shots"],
            "home_shots_ot":     home["shots_ot"],
            "away_shots_ot":     away["shots_ot"],
            "shot_ratio":        home["shots"] / max(away["shots"], 1),
            # Passes
            "home_pass_acc":     home["pass_acc"],
            "away_pass_acc":     away["pass_acc"],
            "pass_acc_diff":     home["pass_acc"] - away["pass_acc"],
            # Pressão
            "home_pressures":    home["pressures"],
            "away_pressures":    away["pressures"],
            "pressure_ratio":    home["pressures"] / max(away["pressures"], 1),
            # Disciplina
            "home_fouls":        home["fouls"],
            "away_fouls":        away["fouls"],
            # Posse/atividade
            "home_carries":      home["carries"],
            "away_carries":      away["carries"],
            # Placar e resultado
            "home_score":        hs,
            "away_score":        as_,
            "result":            0 if hs > as_ else (1 if hs == as_ else 2),
        })

    df = pd.DataFrame(rows)
    dist = df["result"].value_counts().sort_index()
    total = len(df)
    logger.success(
        f"  {total:,} partidas | "
        f"home={dist.get(0,0)/total:.1%} "
        f"draw={dist.get(1,0)/total:.1%} "
        f"away={dist.get(2,0)/total:.1%}"
    )
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 5. ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def build_all_features(save: bool = True):
    logger.info("═══ INICIANDO PIPELINE DE FEATURE ENGINEERING ═══")

    events = load_all_events()

    if save:
        p = PROCESSED_DIR / "events_raw.parquet"
        events.to_parquet(p, index=False)
        logger.info(f"  Eventos brutos salvos: {p}")

    shots_df   = build_shot_features(events)
    fouls_df   = build_foul_features(events)
    matches_df = build_match_features(events)

    if save:
        shots_df.to_csv(PROCESSED_DIR / "shot_features.csv",   index=False)
        fouls_df.to_csv(PROCESSED_DIR / "foul_features.csv",   index=False)
        matches_df.to_csv(PROCESSED_DIR / "match_features.csv", index=False)
        logger.success(f"CSVs salvos em {PROCESSED_DIR}/")

    return shots_df, fouls_df, matches_df


if __name__ == "__main__":
    shots, fouls, matches = build_all_features(save=True)

    print("\n" + "═"*50)
    print("RESUMO FINAL")
    print("═"*50)
    print(f"Chutes:    {len(shots):>7,}  | Gols: {shots['goal'].sum():,} ({shots['goal'].mean():.2%})")
    print(f"Faltas:    {len(fouls):>7,}  | Cartões: {fouls['card_given'].sum():,} ({fouls['card_given'].mean():.2%})")
    print(f"Partidas:  {len(matches):>7,}")
    print(f"\nCSVs em: data/processed/")
    print(f"Próximo:  python src/models/train.py")