import { useState, useEffect } from "react";
import { Activity, Target, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { motion } from "framer-motion";
import { getLiveMatches, startPolling } from "../services/api";

export default function VirtualAssistantSidebar({ activeView, setActiveView, onSelectMatch, selectedMatch }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [liveError, setLiveError] = useState(null);
  const [liveLoading, setLiveLoading] = useState(true);

  const funcoes = [
    { id: 'dashboard', name: "Desempenho da Partida", icon: <Activity size={20} /> },
    { id: 'chat', name: "Probabilidade de Sucesso", icon: <Target size={20} /> }
  ];

  // Polling de jogos ao vivo (30s)
  useEffect(() => {
    const cleanup = startPolling(
      () => getLiveMatches(1),
      (data, err) => {
        setLiveLoading(false);
        if (err) { setLiveError(err.message); return; }
        setLiveMatches((data.matches || []).slice(0, 5)); // Mostra até 5
      },
      30000
    );
    return cleanup;
  }, []);

  return (
    <div className="flex flex-col space-y-8 w-full">
      {/* Outras Funções */}
      <section>
        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">
          Outras Funções
        </h3>
        <ul className="space-y-2">
          {funcoes.map((item) => {
            const isActive = activeView === item.id;

            return (
              <li key={item.id}>
                <button
                  onClick={() => setActiveView(item.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${isActive
                      ? "bg-slate-800 text-brand-yellow shadow-inner"
                      : "text-slate-300 hover:bg-slate-800/50 hover:text-white"
                    }`}
                >
                  {item.icon}
                  <span className="font-medium text-sm">{item.name}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Jogos Ao Vivo */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
            Jogos Ao Vivo
          </h3>
          {!liveError && !liveLoading && (
            <span className="text-green-400 flex items-center gap-1 text-[10px] font-bold uppercase">
              <Wifi size={10} className="animate-pulse" /> Live
            </span>
          )}
          {liveError && (
            <span className="text-red-400 flex items-center gap-1 text-[10px] font-bold uppercase">
              <WifiOff size={10} /> Offline
            </span>
          )}
        </div>

        {/* Loading */}
        {liveLoading && (
          <div className="flex items-center justify-center py-6">
            <RefreshCw size={18} className="text-brand-yellow animate-spin" />
          </div>
        )}

        {/* Error */}
        {liveError && !liveLoading && (
          <p className="text-red-400 text-xs text-center py-4">{liveError}</p>
        )}

        {/* No matches */}
        {!liveLoading && !liveError && liveMatches.length === 0 && (
          <p className="text-slate-500 text-xs text-center py-4">
            Nenhum jogo ao vivo no momento.
          </p>
        )}

        {/* Lista de Jogos */}
        {!liveLoading && !liveError && liveMatches.length > 0 && (
          <div className="grid grid-cols-1 gap-3">
            {liveMatches.map(match => {
              const isSelected = selectedMatch?.event_id === match.event_id;

              return (
                <motion.div
                  key={match.event_id}
                  onClick={() => onSelectMatch?.(match)}
                  whileHover={{ scale: 1.02 }}
                  transition={{ duration: 0.15 }}
                  className={`relative rounded-xl overflow-hidden cursor-pointer shadow-lg border transition-colors p-3 ${isSelected
                      ? "bg-brand-yellow/10 border-brand-yellow/40"
                      : "bg-slate-800/50 border-slate-700 hover:border-slate-600"
                    }`}
                >
                  {/* Ao Vivo Badge */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-500 text-[10px] font-medium uppercase tracking-wider truncate max-w-[70%]">
                      {match.league || "Liga"}
                    </span>
                    <span className="px-1.5 py-0.5 bg-red-600 text-white text-[9px] font-bold rounded flex items-center gap-1 uppercase">
                      <span className="w-1 h-1 rounded-full bg-white animate-pulse" />
                      {match.time ? `${match.time}'` : "Live"}
                    </span>
                  </div>

                  {/* Times + Placar separado por time */}
                  <div className="space-y-1.5">
                    {(() => {
                      const parts = (match.score || "0-0").split("-").map(s => parseInt(s.trim()));
                      const hg = isNaN(parts[0]) ? 0 : parts[0];
                      const ag = isNaN(parts[1]) ? 0 : parts[1];
                      return (
                        <>
                          <div className="flex items-center justify-between">
                            <p className="text-white font-semibold text-xs truncate flex-1 mr-2">{match.home_team}</p>
                            <span className={`text-sm font-bold min-w-[24px] text-center rounded px-1.5 py-0.5 ${
                              hg > ag ? "text-green-400 bg-green-500/10"
                              : hg < ag ? "text-red-400 bg-red-500/10"
                              : "text-slate-300 bg-slate-700/50"
                            }`}>{hg}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <p className="text-slate-400 font-semibold text-xs truncate flex-1 mr-2">{match.away_team}</p>
                            <span className={`text-sm font-bold min-w-[24px] text-center rounded px-1.5 py-0.5 ${
                              ag > hg ? "text-green-400 bg-green-500/10"
                              : ag < hg ? "text-red-400 bg-red-500/10"
                              : "text-slate-300 bg-slate-700/50"
                            }`}>{ag}</span>
                          </div>
                        </>
                      );
                    })()}
                  </div>

                  {/* CTA */}
                  {isSelected && (
                    <div className="mt-2 text-center">
                      <span className="text-brand-yellow text-[10px] font-bold uppercase tracking-wider">
                        ✦ Selecionado
                      </span>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
