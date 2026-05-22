import { useState, useEffect } from "react";
import { Star, Wifi, WifiOff, RefreshCw, Clock, Trophy } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { getLiveMatches, startPolling } from "../services/api";

// Imagens de fallback por esporte
const SPORT_IMAGES = {
  1: "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?auto=format&fit=crop&q=80&w=600",   // Soccer
  18: "https://images.unsplash.com/photo-1542652694-40abf526446e?auto=format&fit=crop&q=80&w=600",      // Basketball
  13: "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?auto=format&fit=crop&q=80&w=600",   // Tennis
};

const SPORT_TABS = [
  { id: 1, name: "Futebol", icon: "⚽", enabled: true },
  { id: 18, name: "Basquete", icon: "🏀", enabled: false },
  { id: 13, name: "Tênis", icon: "🎾", enabled: false },
];

export default function Jogos() {
  const navigate = useNavigate();
  const [activeSport, setActiveSport] = useState(1);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [favorites, setFavorites] = useState(() => {
    try { return JSON.parse(localStorage.getItem("fav_matches") || "[]"); }
    catch { return []; }
  });

  // Polling de partidas ao vivo (30s)
  useEffect(() => {
    setLoading(true);
    setError(null);

    const cleanup = startPolling(
      () => getLiveMatches(),
      (data, err) => {
        setLoading(false);
        if (err) {
          setError(err.message);
          return;
        }
        setMatches(data.matches || []);
        setLastUpdate(new Date());
      },
      60000
    );

    return cleanup;
  }, [activeSport]);

  const toggleFav = (eventId) => {
    setFavorites(prev => {
      const next = prev.includes(eventId)
        ? prev.filter(id => id !== eventId)
        : [...prev, eventId];
      localStorage.setItem("fav_matches", JSON.stringify(next));
      return next;
    });
  };

  const handleMatchClick = (match) => {
    // Navega para o assistente com contexto do jogo
    navigate("/assistente", { state: { selectedMatch: match } });
  };

  return (
    <div className="flex flex-col space-y-8 pb-12 pt-2">

      {/* Header */}
      <div className="text-center mt-6">
        <h1 className="text-3xl md:text-5xl font-light text-white tracking-tight">
          Partidas <span className="font-bold text-brand-yellow">Ao Vivo</span>
        </h1>
        <p className="text-slate-400 mt-3 text-sm md:text-base">
          Clique em um jogo para receber análises e sugestões do assistente
        </p>
      </div>

      {/* Tabs de Esporte */}
      <div className="flex justify-center gap-3">
        {SPORT_TABS.map(sport => (
          <button
            key={sport.id}
            onClick={() => sport.enabled && setActiveSport(sport.id)}
            disabled={!sport.enabled}
            className={`relative px-5 py-2.5 rounded-xl font-bold text-sm transition-all ${
              !sport.enabled
                ? "bg-slate-800/50 text-slate-600 cursor-not-allowed border border-slate-700/50"
                : activeSport === sport.id
                  ? "bg-brand-yellow text-slate-900 shadow-lg shadow-brand-yellow/20"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700"
            }`}
          >
            <span className="mr-1.5">{sport.icon}</span>
            {sport.name}
            {!sport.enabled && (
              <span className="absolute -top-2 -right-2 px-1.5 py-0.5 bg-slate-700 text-slate-400 text-[9px] font-bold rounded-full uppercase">Em breve</span>
            )}
          </button>
        ))}
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between px-2">
        <div className="flex items-center gap-2 text-sm">
          {error ? (
            <span className="text-red-400 flex items-center gap-1.5">
              <WifiOff size={14} /> Offline
            </span>
          ) : (
            <span className="text-green-400 flex items-center gap-1.5">
              <Wifi size={14} className="animate-pulse" /> Ao Vivo
            </span>
          )}
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">{matches.length} jogos</span>
        </div>
        {lastUpdate && (
          <span className="text-slate-500 text-xs flex items-center gap-1">
            <RefreshCw size={12} />
            {lastUpdate.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </span>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <RefreshCw size={32} className="text-brand-yellow animate-spin" />
          <p className="text-slate-400 text-sm">Buscando partidas ao vivo...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4 bg-slate-800/30 rounded-2xl border border-red-500/20 mx-4">
          <WifiOff size={40} className="text-red-400" />
          <p className="text-red-300 text-center max-w-md">{error}</p>
          <button
            onClick={() => { setError(null); setLoading(true); }}
            className="px-4 py-2 bg-slate-700 text-white rounded-lg text-sm hover:bg-slate-600 transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {/* No matches */}
      {!loading && !error && matches.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-4 bg-slate-800/20 rounded-2xl border border-slate-700">
          <Clock size={40} className="text-slate-500" />
          <p className="text-slate-400 text-center">
            Nenhum jogo ao vivo no momento.<br />
            <span className="text-slate-500 text-sm">As partidas aparecem automaticamente quando começam.</span>
          </p>
        </div>
      )}

      {/* Grid de Jogos Ao Vivo */}
      {!loading && !error && matches.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AnimatePresence>
            {matches.map((match) => (
              <motion.div
                key={match.event_id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.2 }}
                onClick={() => handleMatchClick(match)}
                className="relative bg-slate-800/60 backdrop-blur rounded-2xl overflow-hidden cursor-pointer group shadow-xl border border-slate-700 hover:border-brand-yellow/40 transition-colors"
              >
                {/* Gradient top accent */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-brand-yellow via-yellow-500 to-orange-500" />

                <div className="p-5">
                  {/* Liga + Ao Vivo Badge + Favorito */}
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-slate-400 text-xs font-medium uppercase tracking-wider truncate max-w-[60%]">
                      {match.league || "Liga"}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 bg-red-600 text-white text-[10px] font-bold rounded-full flex items-center gap-1.5 uppercase tracking-wider shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                        {match.time ? `${match.time}'` : "Ao Vivo"}
                      </span>
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleFav(match.event_id); }}
                        className="transition-transform hover:scale-110"
                      >
                        <Star
                          size={18}
                          className={favorites.includes(match.event_id)
                            ? "fill-brand-yellow text-brand-yellow drop-shadow-md"
                            : "text-slate-500 hover:text-slate-300"
                          }
                        />
                      </button>
                    </div>
                  </div>

                  {/* Times + Placar */}
                  <div className="flex items-center justify-between">
                    {/* Time Casa */}
                    <div className="flex-1 text-left">
                      <p className="text-white font-bold text-base truncate">{match.home_team}</p>
                    </div>

                    {/* Placar Central */}
                    <div className="px-5 py-2 bg-slate-900/80 rounded-xl mx-3 border border-slate-600">
                      <p className="text-2xl font-extrabold text-white tracking-wider text-center min-w-[4rem]">
                        {match.score || "0-0"}
                      </p>
                    </div>

                    {/* Time Fora */}
                    <div className="flex-1 text-right">
                      <p className="text-white font-bold text-base truncate">{match.away_team}</p>
                    </div>
                  </div>

                  {/* CTA */}
                  <div className="mt-4 flex justify-center">
                    <span className="text-brand-yellow text-xs font-bold uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5">
                      <Trophy size={14} />
                      Analisar com I.A.
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
