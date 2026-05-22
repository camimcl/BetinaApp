/**
 * src/services/api.js
 *
 * Camada de comunicação com o backend FastAPI.
 * Centraliza todas as chamadas HTTP e tratamento de erros.
 *
 * Backend esperado em: http://localhost:8000
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─────────────────────────────────────────────────────────────────────────────
// HELPER
// ─────────────────────────────────────────────────────────────────────────────

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: { "Content-Type": "application/json" },
    ...options,
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      // FastAPI 422 retorna detail como array: [{"loc":[...], "msg":"...", "type":"..."}]
      let message = `Erro ${response.status}`;
      if (Array.isArray(error.detail)) {
        message = error.detail.map(e => `${e.loc?.join(".") || ""}: ${e.msg}`).join("; ");
      } else if (typeof error.detail === "string") {
        message = error.detail;
      }
      throw new Error(message);
    }

    return await response.json();
  } catch (err) {
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      throw new Error("Não foi possível conectar ao servidor. Verifique se o backend está rodando.");
    }
    throw err;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// HEALTH
// ─────────────────────────────────────────────────────────────────────────────

/** Verifica status da API e modelos carregados */
export async function getHealth() {
  return request("/health");
}

// ─────────────────────────────────────────────────────────────────────────────
// LIVE MATCHES (API-Football)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Busca partidas ao vivo.
 */
export async function getLiveMatches() {
  return request(`/live/matches`);
}

/**
 * Busca detalhes + odds de uma partida ao vivo.
 * @param {string} eventId - ID do fixture API-Football
 */
export async function getLiveMatchDetail(eventId) {
  return request(`/live/match/${eventId}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// PREDIÇÕES
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Prediz P(gol) dado um chute.
 * Retorna probabilidade, fatores SHAP e narrativa em PT-BR.
 */
export async function predictShot(shotData) {
  return request("/predict/shot", {
    method: "POST",
    body: JSON.stringify(shotData),
  });
}

/**
 * Prediz P(cartão) dada uma falta.
 * Retorna probabilidade, fatores SHAP e narrativa em PT-BR.
 */
export async function predictFoul(foulData) {
  return request("/predict/foul", {
    method: "POST",
    body: JSON.stringify(foulData),
  });
}

/**
 * Prediz P(resultado) de uma partida.
 * Retorna probabilidades para casa/empate/fora + narrativa Gemini.
 * @param {Object} matchData - inclui home_team_name e away_team_name
 */
export async function predictMatch(matchData) {
  return request("/predict/match", {
    method: "POST",
    body: JSON.stringify(matchData),
  });
}

/**
 * Chat conversacional com a Betina via Gemini.
 * Mantém histórico multi-turn por session_id no backend.
 * @param {Object} payload - { session_id, message, match_context? }
 */
export async function chatBetina(payload) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// SIMULAÇÃO "E SE?"
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Motor de simulação hipotética.
 * @param {Object} simData - { prediction_type, base_data, overrides, description }
 */
export async function simulateWhatIf(simData) {
  return request("/simulate", {
    method: "POST",
    body: JSON.stringify(simData),
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// UTILITÁRIOS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Polling — busca dados periodicamente.
 * @param {Function} fetchFn - Função async que busca dados
 * @param {Function} onData - Callback com os dados
 * @param {number} intervalMs - Intervalo em ms (default 30s)
 * @returns {Function} cleanup — chame para parar o polling
 */
export function startPolling(fetchFn, onData, intervalMs = 30000) {
  let active = true;

  const poll = async () => {
    if (!active) return;
    try {
      const data = await fetchFn();
      if (active) onData(data, null);
    } catch (err) {
      if (active) onData(null, err);
    }
    if (active) setTimeout(poll, intervalMs);
  };

  poll(); // primeira chamada imediata

  return () => { active = false; };
}
