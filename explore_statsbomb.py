"""
explore_statsbomb.py

Roda ANTES de qualquer treinamento.
Mostra tudo que o StatsBomb Open Data oferece:
competições, temporadas, jogos disponíveis e estrutura dos eventos.

Execute:
    python explore_statsbomb.py
"""

import pandas as pd
from statsbombpy import sb
from loguru import logger

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 120)


def explore_competitions():
    logger.info("=== COMPETIÇÕES DISPONÍVEIS ===")
    comps = sb.competitions()
    print(comps[["competition_id", "competition_name", "season_id", "season_name"]].to_string(index=False))
    return comps


def explore_matches(competition_id: int, season_id: int, label: str):
    logger.info(f"=== PARTIDAS: {label} ===")
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    print(f"Total de partidas: {len(matches)}")
    print(matches[["match_id", "match_date", "home_team", "away_team", "home_score", "away_score"]].head(5).to_string(index=False))
    return matches


def explore_events(match_id: int):
    logger.info(f"=== EVENTOS DA PARTIDA {match_id} ===")
    events = sb.events(match_id=match_id)

    print(f"\nTotal de eventos: {len(events)}")
    print(f"\nTipos de eventos disponíveis:")
    print(events["type"].value_counts().to_string())

    # Estrutura de um chute
    shots = events[events["type"] == "Shot"]
    print(f"\n--- Exemplo de CHUTE (colunas disponíveis) ---")
    shot_cols = [c for c in shots.columns if not shots[c].isna().all()]
    print(shot_cols)
    if len(shots) > 0:
        print(shots[shot_cols].iloc[0])

    # Estrutura de uma falta
    fouls = events[events["type"] == "Foul Committed"]
    print(f"\n--- Exemplo de FALTA (colunas disponíveis) ---")
    foul_cols = [c for c in fouls.columns if not fouls[c].isna().all()]
    print(foul_cols)

    return events


def explore_360(match_id: int):
    """Dados de posicionamento 360° — nem todos os jogos têm."""
    logger.info(f"=== DADOS 360° DA PARTIDA {match_id} ===")
    try:
        frames = sb.frames(match_id=match_id)
        print(f"Total de frames 360°: {len(frames)}")
        print(frames.columns.tolist())
        print(frames.head(2))
        return frames
    except Exception as e:
        logger.warning(f"Sem dados 360° para partida {match_id}: {e}")
        return None


def volume_summary(comps: pd.DataFrame):
    """
    Conta quantas partidas existem nas competições mais ricas.
    Útil para decidir onde focar o treinamento.
    """
    logger.info("=== VOLUME POR COMPETIÇÃO ===")

    # Competições que sabemos que têm bastante dado
    targets = [
        (11, 90,  "La Liga 2015/16"),
        (11, 42,  "La Liga 2019/20"),
        (2,  44,  "Premier League 2003/04"),
        (16, 4,   "UEFA Euro 2020"),
        (43, 106, "FIFA World Cup 2022"),
        (3,  90,  "1. Bundesliga 2015/16"),
    ]

    rows = []
    for cid, sid, label in targets:
        try:
            matches = sb.matches(competition_id=cid, season_id=sid)
            rows.append({"Competição": label, "Partidas": len(matches), "competition_id": cid, "season_id": sid})
        except Exception as e:
            rows.append({"Competição": label, "Partidas": "ERRO", "competition_id": cid, "season_id": sid})

    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))
    return summary


if __name__ == "__main__":
    # 1. Lista todas as competições
    comps = explore_competitions()

    print("\n" + "="*60 + "\n")

    # 2. Volume por competição-alvo
    summary = volume_summary(comps)

    print("\n" + "="*60 + "\n")

    # 3. Detalha La Liga 2015/16 (competition_id=11, season_id=90)
    #    É a competição mais completa do StatsBomb Open Data
    matches_laliga = explore_matches(11, 90, "La Liga 2015/16")

    print("\n" + "="*60 + "\n")

    # 4. Pega o primeiro jogo e explora os eventos
    if len(matches_laliga) > 0:
        first_match_id = matches_laliga.iloc[0]["match_id"]
        events = explore_events(first_match_id)

        print("\n" + "="*60 + "\n")

        # 5. Tenta dados 360°
        explore_360(first_match_id)
