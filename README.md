# 🏟️ IntelliBet — Análise Esportiva com IA

Plataforma de análise esportiva inteligente com XGBoost + SHAP + Gemini AI + API-Football.  
Assistente virtual **Elli AI** integrada via chat e Telegram.

---

## ⚙️ Configuração do Ambiente

### 1. Crie e ative o ambiente virtual
```bash
python -m venv venv
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente
```bash
cp .env.example .env
# Edite .env e coloque seu FOOTBALL_API_KEY (grátis em https://dashboard.api-football.com/register)
```

---

## 🚀 Fluxo de Desenvolvimento (em ordem)

### Passo 1 — Explorar os dados do StatsBomb
```bash
python explore_statsbomb.py
```
Isso mostra todas as competições disponíveis, volume de partidas e estrutura dos eventos.
Nenhum download manual necessário — o `statsbombpy` busca automaticamente.

### Passo 2 — Gerar features (pode demorar 10–30 min)
```bash
python src/data/feature_builder.py
```
Isso carrega todos os jogos das competições configuradas, extrai features
e salva CSVs em `data/processed/`:
- `shot_features.csv`
- `foul_features.csv`
- `match_features.csv`

### Passo 3 — Treinar os modelos
```bash
python src/models/train.py
```
Treina 3 modelos XGBoost com validação temporal e SHAP.
Salva os modelos em `data/models/`.

### Passo 4 — Rodar a API
```bash
uvicorn src.api.main:app --reload --port 8000
```
Acesse a documentação interativa em: http://localhost:8000/docs

---

## 📡 Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Status da API e modelos |
| POST | `/predict/shot` | P(gol) dado um chute |
| POST | `/predict/foul` | P(cartão) dada uma falta |
| POST | `/predict/match` | P(resultado) de uma partida |
| POST | `/simulate` | Cenário "E SE?" |
| GET | `/live/matches` | Partidas ao vivo (API-Football) |
| GET | `/live/match/{id}` | Detalhes de partida ao vivo |

---

## 🎯 Exemplo de uso — Simulação "E SE?"

```json
POST /simulate
{
  "prediction_type": "shot",
  "description": "E se o chute fosse de dentro da área, sem pressão?",
  "base_data": {
    "distance_to_goal": 25.0,
    "angle_to_goal": 15.0,
    "xg": 0.05,
    "technique": "Normal",
    "body_part": "Right Foot",
    "shot_type": "Open Play",
    "first_time": 0,
    "open_goal": 0,
    "under_pressure": 1,
    "minute": 60.0,
    "time_seconds": 3600.0,
    "is_second_half": 1,
    "is_extra_time": 0,
    "score_diff": 0,
    "is_home_team": 1
  },
  "overrides": {
    "distance_to_goal": 10.0,
    "angle_to_goal": 35.0,
    "xg": 0.25,
    "under_pressure": 0
  }
}
```

---

## 📁 Estrutura do Projeto

```
project/
├── data/
│   ├── processed/       # CSVs de features geradas
│   └── models/          # Modelos treinados (.pkl)
├── src/
│   ├── data/
│   │   └── feature_builder.py   # Pipeline de extração e features
│   ├── models/
│   │   ├── train.py             # Treinamento XGBoost + SHAP
│   │   └── predictor.py         # Predições + simulação "E SE?"
│   └── api/
│       └── main.py              # FastAPI
├── explore_statsbomb.py         # Script de exploração dos dados
├── requirements.txt
└── .env.example
```

---

## 🧠 Modelos

| Modelo | Features principais | Target | Métrica alvo |
|--------|--------------------|---------|----|
| GoalModel | xG, distância, ângulo, técnica, pressão | gol (0/1) | AUC > 0.80 |
| CardModel | localização, minuto, time perdendo | cartão (0/1) | AUC > 0.72 |
| MatchModel | xG, chutes, passes, pressão | resultado (3 classes) | Acc > 0.55 |

### Por que XGBoost?
- Lida bem com features mistas (numéricas + categóricas)
- SHAP nativo — explicabilidade por predição
- Robusto com dados desbalanceados (gols são ~10% dos chutes)
- Treinamento rápido, inferência em tempo real

### Por que split temporal?
Dados esportivos têm dependência temporal (times evoluem, jogadores mudam).
Split aleatório vazaria informação do futuro para o treino, inflando as métricas.
