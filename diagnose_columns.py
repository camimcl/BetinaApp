"""
diagnose_columns.py

Roda ANTES de qualquer coisa quando o feature_builder der erro.
Mostra EXATAMENTE quais colunas existem nos eventos do StatsBomb
para que possamos mapear corretamente no feature_builder.

Execute:
    python diagnose_columns.py
"""

import pandas as pd
from statsbombpy import sb

# Pega a primeira partida disponível (La Liga 2015/16)
print("Carregando partidas La Liga 2015/16...")
matches = sb.matches(competition_id=11, season_id=90)
match_id = matches.iloc[0]["match_id"]
print(f"Usando match_id: {match_id}\n")

events = sb.events(match_id=match_id)

print("=" * 60)
print("TODOS OS TIPOS DE EVENTO:")
print(events["type"].value_counts())

print("\n" + "=" * 60)
print("TODAS AS COLUNAS DO DATAFRAME:")
for col in sorted(events.columns):
    non_null = events[col].notna().sum()
    print(f"  {col:45s} não-nulos: {non_null}")

print("\n" + "=" * 60)
print("COLUNAS DE CHUTE (contém 'shot'):")
shot_cols = [c for c in events.columns if "shot" in c.lower()]
for col in shot_cols:
    print(f"  {col}")

print("\n" + "=" * 60)
print("COLUNAS DE FALTA (contém 'foul'):")
foul_cols = [c for c in events.columns if "foul" in c.lower()]
for col in foul_cols:
    print(f"  {col}")

print("\n" + "=" * 60)
print("COLUNAS DE CARTÃO (contém 'card' ou 'bad'):")
card_cols = [c for c in events.columns if "card" in c.lower() or "bad" in c.lower()]
for col in card_cols:
    print(f"  {col}")

# Mostra um chute real para ver os valores
shots = events[events["type"] == "Shot"]
print("\n" + "=" * 60)
print(f"EXEMPLO DE CHUTE (linha completa, {len(shots)} chutes nessa partida):")
if len(shots) > 0:
    sample = shots.iloc[0]
    for col in sorted(shots.columns):
        val = sample[col]
        if pd.notna(val) and val != "" and val != []:
            print(f"  {col:45s} = {val}")

# Mostra uma falta real
fouls = events[events["type"] == "Foul Committed"]
print("\n" + "=" * 60)
print(f"EXEMPLO DE FALTA ({len(fouls)} faltas nessa partida):")
if len(fouls) > 0:
    sample = fouls.iloc[0]
    for col in sorted(fouls.columns):
        val = sample[col]
        if pd.notna(val) and val != "" and val != []:
            print(f"  {col:45s} = {val}")