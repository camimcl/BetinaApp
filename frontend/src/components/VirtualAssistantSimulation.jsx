import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Play, ArrowRight, TrendingUp, TrendingDown, Minus, RotateCcw, Info } from "lucide-react";
import { simulateWhatIf } from "../services/api";

/**
 * VirtualAssistantSimulation — Interface do motor "E SE?"
 *
 * Permite ao usuário definir um cenário base, alterar variáveis e ver
 * como as probabilidades mudam. Usado para simular diferentes cenários de aposta.
 */

const SIMULATION_TYPES = [
  {
    id: "shot",
    name: "Chute → Gol",
    emoji: "⚽",
    description: "E se o chute fosse diferente?",
    baseFields: [
      { key: "distance_to_goal", label: "Distância ao gol (m)", value: 18, min: 1, max: 50 },
      { key: "angle_to_goal", label: "Ângulo para o gol (°)", value: 25, min: 1, max: 60 },
      { key: "xg", label: "Chance Real de Sair Gol", value: 0.12, min: 0, max: 1, step: 0.01 },
      { key: "under_pressure", label: "Sob pressão?", value: 1, type: "toggle" },
      { key: "first_time", label: "Chute de primeira?", value: 0, type: "toggle" },
      { key: "open_goal", label: "Gol aberto?", value: 0, type: "toggle" },
      { key: "minute", label: "Minuto", value: 60, min: 1, max: 120 },
      { key: "score_diff", label: "Diff. placar", value: 0, min: -5, max: 5 },
      { key: "is_home_team", label: "Time da casa?", value: 1, type: "toggle" },
    ],
    defaults: {
      technique: "Normal",
      body_part: "Right Foot",
      shot_type: "Open Play",
      time_seconds: 3600,
      is_second_half: 1,
      is_extra_time: 0,
    },
  },
  {
    id: "foul",
    name: "Falta → Cartão",
    emoji: "🟨",
    description: "E se a falta fosse diferente?",
    baseFields: [
      { key: "x", label: "Posição X (campo)", value: 75, min: 0, max: 120 },
      { key: "y", label: "Posição Y (campo)", value: 40, min: 0, max: 80 },
      { key: "dist_to_center", label: "Dist. ao centro", value: 25, min: 0, max: 60 },
      { key: "in_danger_zone", label: "Zona de perigo?", value: 0, type: "toggle" },
      { key: "in_final_third", label: "Terço final?", value: 1, type: "toggle" },
      { key: "minute", label: "Minuto", value: 78, min: 1, max: 120 },
      { key: "under_pressure", label: "Sob pressão?", value: 1, type: "toggle" },
      { key: "score_diff", label: "Diff. placar", value: -1, min: -5, max: 5 },
      { key: "team_losing", label: "Time perdendo?", value: 1, type: "toggle" },
      { key: "is_home_team", label: "Time da casa?", value: 1, type: "toggle" },
    ],
    defaults: {
      foul_type: "Regular",
      advantage: 0,
      time_seconds: 4680,
      is_second_half: 1,
      is_last_10_min: 0,
    },
  },
  {
    id: "match",
    name: "Resultado da Partida",
    emoji: "🏆",
    description: "E se as estatísticas do jogo fossem diferentes?",
    baseFields: [
      { key: "home_score", label: "Gols do Mandante (Ajuste)", value: 0, min: 0, max: 10 },
      { key: "away_score", label: "Gols do Visitante (Ajuste)", value: 0, min: 0, max: 10 },
      { key: "minute", label: "Minuto (Tempo Restante)", value: 45, min: 1, max: 120 },
      { key: "home_xg", label: "Volume de Oportunidades (Casa)", value: 1.5, min: 0, max: 5, step: 0.1 },
      { key: "away_xg", label: "Volume de Oportunidades (Fora)", value: 0.8, min: 0, max: 5, step: 0.1 },
      { key: "xg_diff", label: "Diferença de Oportunidades", value: 0.7, min: -4, max: 4, step: 0.1 },
      { key: "home_shots", label: "Total de Finalizações (Casa)", value: 12, min: 0, max: 30 },
      { key: "away_shots", label: "Total de Finalizações (Fora)", value: 6, min: 0, max: 30 },
      { key: "home_shots_ot", label: "Chutes na Direção do Gol (Casa)", value: 5, min: 0, max: 20 },
      { key: "away_shots_ot", label: "Chutes na Direção do Gol (Fora)", value: 2, min: 0, max: 20 },
      { key: "home_pass_acc", label: "Efetividade da Posse (Casa)", value: 0.84, min: 0.4, max: 1, step: 0.01 },
      { key: "away_pass_acc", label: "Efetividade da Posse (Fora)", value: 0.78, min: 0.4, max: 1, step: 0.01 },
      { key: "pressure_ratio", label: "Domínio Territorial (>1 = Casa domina)", value: 1.3, min: 0.3, max: 3, step: 0.1 },
    ],
    defaults: {
      home_passes: 450,
      away_passes: 320,
      home_pressures: 120,
      away_pressures: 90,
      home_fouls: 10,
      away_fouls: 14,
    },
  },
];

export default function VirtualAssistantSimulation({ selectedMatch }) {
  const [simType, setSimType] = useState(SIMULATION_TYPES[0]);
  const [baseValues, setBaseValues] = useState(() => buildInitialValues(SIMULATION_TYPES[0]));
  const [overrides, setOverrides] = useState({});
  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function buildInitialValues(type) {
    const values = { ...type.defaults };
    type.baseFields.forEach(f => { values[f.key] = f.value; });
    return values;
  }

  useEffect(() => {
    // Sincroniza simulação E Se com a partida observada na barra lateral
    if (selectedMatch && simType.id === "match" && Object.keys(overrides).length === 0) {
      const ms = selectedMatch.stats || {};
      setBaseValues(prev => ({
        ...prev,
        home_score: selectedMatch.home_score ?? prev.home_score,
        away_score: selectedMatch.away_score ?? prev.away_score,
        minute: selectedMatch.time ? parseInt(selectedMatch.time.replace("'", "")) || prev.minute : prev.minute,
        home_xg: ms.home_xg ?? prev.home_xg,
        away_xg: ms.away_xg ?? prev.away_xg,
        xg_diff: ms.xg_diff ?? prev.xg_diff,
        home_shots: ms.home_shots ?? prev.home_shots,
        away_shots: ms.away_shots ?? prev.away_shots,
        home_shots_ot: ms.home_shots_ot ?? prev.home_shots_ot,
        away_shots_ot: ms.away_shots_ot ?? prev.away_shots_ot,
        home_pass_acc: ms.home_pass_acc ?? prev.home_pass_acc,
        away_pass_acc: ms.away_pass_acc ?? prev.away_pass_acc,
        pressure_ratio: ms.pressure_ratio ?? prev.pressure_ratio
      }));
    }
  }, [selectedMatch, simType]);

  function handleTypeChange(type) {
    setSimType(type);
    setBaseValues(buildInitialValues(type));
    setOverrides({});
    setResult(null);
    setError(null);
  }

  function handleBaseChange(key, val) {
    setBaseValues(prev => ({ ...prev, [key]: val }));
  }

  function handleOverrideChange(key, val) {
    setOverrides(prev => {
      const next = { ...prev };
      if (val === "" || val === undefined) {
        delete next[key];
      } else {
        next[key] = val;
      }
      return next;
    });
  }

  async function handleSimulate() {
    if (Object.keys(overrides).length === 0) {
      setError("Altere pelo menos uma variável no cenário hipotético!");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await simulateWhatIf({
        prediction_type: simType.id,
        base_data: baseValues,
        overrides,
        description: description || `Simulação ${simType.name}`,
      });
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setOverrides({});
    setResult(null);
    setError(null);
    setDescription("");
  }

  return (
    <div className="flex flex-col h-[calc(100vh-14rem)] bg-slate-800/30 rounded-2xl border border-slate-700 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700 bg-slate-800/90 backdrop-blur-md shrink-0">
        <div>
          <h2 className="text-lg font-bold text-white">
            🔮 Simulação <span className="text-brand-yellow">"E SE?"</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Altere variáveis e veja como as probabilidades mudam
          </p>
        </div>
        <button onClick={handleReset} className="text-slate-400 hover:text-white transition-colors p-2 rounded-lg hover:bg-slate-700">
          <RotateCcw size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {/* Tipo de Simulação */}
        <div className="flex gap-2">
          {SIMULATION_TYPES.map(type => (
            <button
              key={type.id}
              onClick={() => handleTypeChange(type)}
              className={`flex-1 p-3 rounded-xl text-sm font-bold transition-all ${simType.id === type.id
                  ? "bg-brand-yellow text-slate-900 shadow-lg"
                  : "bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700"
                }`}
            >
              <span className="text-lg">{type.emoji}</span>
              <p className="mt-1 text-xs">{type.name}</p>
            </button>
          ))}
        </div>

        {/* Alerta contextual */}
        {selectedMatch && simType.id === "match" ? (
          <div className="bg-brand-yellow/10 border border-brand-yellow/30 p-3 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Info size={18} className="text-brand-yellow shrink-0" />
              <div>
                <p className="text-sm font-bold text-white">
                  Vinculado: {selectedMatch.home_team} vs {selectedMatch.away_team}
                </p>
                <p className="text-xs text-slate-400">
                  O Cenário Base foi ajustado para espelhar as estatísticas atuais deste jogo.
                </p>
              </div>
            </div>
            <div className="text-right shrink-0 px-2">
               <span className="bg-slate-800 text-brand-yellow text-xs font-bold px-2 py-1 flex items-center gap-1 rounded border border-brand-yellow/30">{selectedMatch.home_score} - {selectedMatch.away_score}</span>
            </div>
          </div>
        ) : !selectedMatch && simType.id === "match" ? (
          <div className="bg-slate-800/80 border border-slate-700 p-3 rounded-xl flex items-start gap-3">
            <Info size={18} className="text-slate-400 shrink-0" />
            <div>
              <p className="text-sm font-bold text-slate-300">Modo Sandbox Teórico</p>
              <p className="text-xs text-slate-500">Selecione uma partida ao vivo na barra lateral para que a I.A. teste cenários com os dados reais em andamento.</p>
            </div>
          </div>
        ) : null}

        {/* Descrição */}
        <input
          type="text"
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder={simType.description}
          className="w-full bg-slate-800 text-white rounded-xl px-4 py-3 border border-slate-700 text-sm placeholder-slate-500 focus:outline-none focus:border-brand-yellow/50"
        />

        {/* Campos lado a lado: Base | Hipotético */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Cenário Base */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <h3 className="text-white font-bold text-sm mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              Cenário Base (Real)
            </h3>
            <div className="space-y-3">
              {simType.baseFields.map(field => (
                <div key={field.key} className="flex items-center justify-between">
                  <label className="text-slate-400 text-xs flex-1">{field.label}</label>
                  {field.type === "toggle" ? (
                    <button
                      onClick={() => handleBaseChange(field.key, baseValues[field.key] ? 0 : 1)}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${baseValues[field.key]
                          ? "bg-green-500/20 text-green-400 border border-green-500/30"
                          : "bg-slate-700 text-slate-400 border border-slate-600"
                        }`}
                    >
                      {baseValues[field.key] ? "Sim" : "Não"}
                    </button>
                  ) : (
                    <input
                      type="number"
                      value={baseValues[field.key]}
                      onChange={e => handleBaseChange(field.key, parseFloat(e.target.value) || 0)}
                      min={field.min}
                      max={field.max}
                      step={field.step || 1}
                      className="w-20 bg-slate-700 text-white text-xs text-center rounded-lg px-2 py-1.5 border border-slate-600 focus:outline-none focus:border-blue-400"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Cenário Hipotético (Overrides) */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-brand-yellow/20">
            <h3 className="text-brand-yellow font-bold text-sm mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-yellow" />
              Cenário "E SE?" (Alterações)
            </h3>
            <div className="space-y-3">
              {simType.baseFields.map(field => {
                const hasOverride = field.key in overrides;
                return (
                  <div key={field.key} className="flex items-center justify-between">
                    <label className={`text-xs flex-1 ${hasOverride ? "text-brand-yellow" : "text-slate-500"}`}>
                      {field.label}
                    </label>
                    {field.type === "toggle" ? (
                      <button
                        onClick={() => {
                          const current = overrides[field.key] ?? baseValues[field.key];
                          handleOverrideChange(field.key, current ? 0 : 1);
                        }}
                        className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${(overrides[field.key] ?? baseValues[field.key])
                            ? "bg-brand-yellow/20 text-brand-yellow border border-brand-yellow/30"
                            : "bg-slate-700 text-slate-400 border border-slate-600"
                          }`}
                      >
                        {(overrides[field.key] ?? baseValues[field.key]) ? "Sim" : "Não"}
                      </button>
                    ) : (
                      <input
                        type="number"
                        value={overrides[field.key] ?? ""}
                        onChange={e => handleOverrideChange(field.key, e.target.value !== "" ? parseFloat(e.target.value) : "")}
                        min={field.min}
                        max={field.max}
                        step={field.step || 1}
                        placeholder={String(baseValues[field.key])}
                        className={`w-20 text-xs text-center rounded-lg px-2 py-1.5 border focus:outline-none ${hasOverride
                            ? "bg-brand-yellow/10 text-brand-yellow border-brand-yellow/30 focus:border-brand-yellow"
                            : "bg-slate-700 text-slate-500 border-slate-600 focus:border-slate-400"
                          }`}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Botão Simular */}
        <button
          onClick={handleSimulate}
          disabled={loading}
          className="w-full py-3.5 bg-brand-yellow hover:bg-yellow-400 text-slate-900 font-bold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-brand-yellow/20"
        >
          {loading ? (
            <>
              <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                <Play size={18} />
              </motion.div>
              Simulando...
            </>
          ) : (
            <>
              <Play size={18} />
              Rodar Simulação
            </>
          )}
        </button>

        {/* Erro */}
        {error && (
          <div className="bg-red-900/30 border border-red-700/30 rounded-xl p-4 text-red-300 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Resultado */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* Delta visual */}
            <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
              <h3 className="text-white font-bold text-sm mb-4 flex items-center gap-2">
                📊 Resultado da Simulação
              </h3>

              {Object.entries(result.delta || {}).map(([key, delta]) => {
                const pct = (delta * 100).toFixed(1);
                const isPositive = delta > 0;
                const isZero = Math.abs(delta) < 0.001;

                return (
                  <div key={key} className="flex items-center gap-3 mb-3">
                    <div className={`p-2 rounded-lg ${isZero ? "bg-slate-700" : isPositive ? "bg-green-500/20" : "bg-red-500/20"}`}>
                      {isZero ? <Minus size={18} className="text-slate-400" /> :
                        isPositive ? <TrendingUp size={18} className="text-green-400" /> :
                          <TrendingDown size={18} className="text-red-400" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-slate-400 text-xs">{key.replace(/_/g, " ")}</p>
                      <p className={`text-lg font-bold ${isZero ? "text-slate-300" : isPositive ? "text-green-400" : "text-red-400"}`}>
                        {isPositive ? "+" : ""}{pct} p.p.
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-slate-500 text-xs">Base → Hipotético</p>
                      <p className="text-white text-sm font-medium">
                        {((result.base?.[key] || 0) * 100).toFixed(1)}%
                        <ArrowRight size={12} className="inline mx-1 text-slate-500" />
                        {((result.simulated?.[key] || 0) * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Narrativa */}
            <div className="bg-gradient-to-br from-brand-yellow/10 to-yellow-500/5 rounded-xl p-5 border border-brand-yellow/20">
              <h3 className="text-brand-yellow font-bold text-sm mb-3 flex items-center gap-2">
                <Info size={16} />
                Explicação da Elli AI
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">
                {result.narrative}
              </p>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
