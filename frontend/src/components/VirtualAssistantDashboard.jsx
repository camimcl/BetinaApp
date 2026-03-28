import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Activity, Loader2, AlertCircle } from 'lucide-react';
import AreaChartPerformance from './charts/AreaChartPerformance';
import BarChartAnalytics from './charts/BarChartAnalytics';
import { predictMatch, getLiveMatchDetail } from '../services/api';

export default function VirtualAssistantDashboard({ selectedMatch }) {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Quando um jogo é selecionado → busca predição
  useEffect(() => {
    if (!selectedMatch) return;
    fetchPrediction(selectedMatch);
  }, [selectedMatch?.event_id]);

  async function fetchPrediction(match) {
    setLoading(true);
    setError(null);

    try {
      const score = (match.score || "0-0").split("-").map(Number);
      const homeScore = score[0] || 0;
      const awayScore = score[1] || 0;

      const matchData = {
        home_team_name: match.home_team || "Mandante",
        away_team_name: match.away_team || "Visitante",
        home_score: homeScore,
        away_score: awayScore,
        minute: parseInt(match.time) || 45,
        home_xg: homeScore * 1.1 + 0.3,
        away_xg: awayScore * 1.1 + 0.3,
        xg_diff: (homeScore - awayScore) * 1.1,
        home_shots: Math.floor(Math.max(homeScore * 4, 3)),
        away_shots: Math.floor(Math.max(awayScore * 4, 3)),
        home_shots_ot: Math.floor(Math.max(homeScore * 2, 1)),
        away_shots_ot: Math.floor(Math.max(awayScore * 2, 1)),
        home_passes: Math.floor(300 + Math.random() * 200),
        away_passes: Math.floor(300 + Math.random() * 200),
        home_pass_acc: +(0.75 + Math.random() * 0.15).toFixed(2),
        away_pass_acc: +(0.75 + Math.random() * 0.15).toFixed(2),
        home_pressures: Math.floor(60 + Math.random() * 80),
        away_pressures: Math.floor(60 + Math.random() * 80),
        pressure_ratio: +(0.8 + Math.random() * 0.8).toFixed(2),
        home_fouls: Math.floor(5 + Math.random() * 10),
        away_fouls: Math.floor(5 + Math.random() * 10),
      };

      const pred = await predictMatch(matchData);
      setPrediction(pred);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col space-y-6 bg-slate-800/20 rounded-[2rem] p-6 lg:p-8 border border-slate-700 shadow-2xl h-[calc(100vh-14rem)] overflow-y-auto"
    >
      <div className="flex items-center justify-between border-b border-slate-700/60 pb-4 shrink-0">
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Painel de <span className="text-brand-yellow">Estatísticas</span>
        </h2>
        <span className="bg-brand-yellow/20 text-brand-yellow text-[10px] md:text-xs font-bold px-3 py-1.5 rounded-full flex items-center shadow-inner uppercase tracking-wider">
          <Activity size={14} className="mr-1.5 animate-pulse" /> Tempo Real
        </span>
      </div>

      {/* Predição do jogo selecionado */}
      {selectedMatch && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold text-base">
              {selectedMatch.home_team} <span className="text-brand-yellow">{selectedMatch.score || "0-0"}</span> {selectedMatch.away_team}
            </h3>
            {selectedMatch.time && (
              <span className="px-2 py-1 bg-red-600 text-white text-[10px] font-bold rounded-full flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                {selectedMatch.time}'
              </span>
            )}
          </div>

          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={24} className="text-brand-yellow animate-spin" />
              <span className="text-slate-400 text-sm ml-3">Analisando...</span>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-3 py-4 text-red-400 text-sm">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {prediction && !loading && (
            <div className="space-y-4">
              {/* Barras de probabilidade */}
              <div className="space-y-3">
                {[
                  { label: selectedMatch.home_team || "Casa", prob: prediction.home_win_probability, color: "bg-green-500" },
                  { label: "Empate", prob: prediction.draw_probability, color: "bg-slate-400" },
                  { label: selectedMatch.away_team || "Visitante", prob: prediction.away_win_probability, color: "bg-red-500" },
                ].map(item => (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-300 font-medium">{item.label}</span>
                      <span className="text-white font-bold">{(item.prob * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-3">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${item.prob * 100}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                        className={`${item.color} h-3 rounded-full`}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Fatores SHAP */}
              {prediction.factors && prediction.factors.length > 0 && (
                <div className="mt-4 bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                  <h4 className="text-slate-400 font-bold text-xs uppercase tracking-wider mb-3">Fatores Principais</h4>
                  <div className="space-y-2">
                    {prediction.factors.slice(0, 3).map((factor, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-slate-300">{factor.label}</span>
                        <span className={`font-bold text-xs px-2 py-0.5 rounded ${
                          factor.direction === "aumenta"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-red-500/20 text-red-400"
                        }`}>
                          {factor.direction === "aumenta" ? "↑" : "↓"} {Math.abs(factor.shap_value).toFixed(3)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Gráficos existentes (históricos) */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6 shadow-xl">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-slate-400 font-bold text-xs uppercase tracking-widest">Meu Desempenho</h3>
              <p className="text-3xl font-extrabold text-white mt-1">R$ 7.500<span className="text-xl font-medium text-slate-500">,00</span></p>
            </div>
            <div className="bg-green-500/20 text-green-400 p-2 rounded-lg flex items-center shadow-inner border border-green-500/10">
              <TrendingUp size={16} className="mr-1" />
              <span className="font-bold text-sm">+42%</span>
            </div>
          </div>
          <AreaChartPerformance />
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6 shadow-xl">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-slate-400 font-bold text-xs uppercase tracking-widest">Meus Desempenhos</h3>
              <p className="text-[10px] uppercase font-bold text-brand-yellow mt-2 tracking-widest">Visão Geral Semanal</p>
            </div>
          </div>
          <BarChartAnalytics />
        </div>
      </div>

      {/* Sumário IA */}
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 text-center shadow-inner mt-auto shrink-0">
        <p className="text-slate-400 text-sm md:text-[15px] leading-relaxed max-w-3xl mx-auto">
          {prediction ? (
            <>
              A I.A. analisou <strong className="text-white">{selectedMatch?.home_team} vs {selectedMatch?.away_team}</strong>.{' '}
              O cenário mais provável é <strong className="text-brand-yellow">{prediction.dominant_outcome}</strong>.{' '}
              Use a aba de Simulação para testar cenários alternativos.
            </>
          ) : (
            <>
              Selecione um jogo ao vivo na barra lateral para ver análises em tempo real.{' '}
              A I.A. calcula probabilidades usando <strong className="text-white">XGBoost + SHAP</strong> com dados do StatsBomb.
            </>
          )}
        </p>
      </div>
    </motion.div>
  );
}
