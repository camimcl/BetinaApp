import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import VirtualAssistantSidebar from "../components/VirtualAssistantSidebar";
import VirtualAssistantChat from "../components/VirtualAssistantChat";
import VirtualAssistantDashboard from "../components/VirtualAssistantDashboard";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Tv2 } from "lucide-react";

export default function AssistenteVirtual() {
  const [activeView, setActiveView] = useState("chat");
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false); // mobile: sidebar colapsada por padrão
  const location = useLocation();

  // Se veio da página de Jogos com um jogo selecionado
  useEffect(() => {
    if (location.state?.selectedMatch) {
      setSelectedMatch(location.state.selectedMatch);
      setActiveView("chat");
    }
  }, [location.state]);

  const handleSelectMatch = (match) => {
    setSelectedMatch(match);
    if (activeView !== "chat") setActiveView("chat");
    setSidebarOpen(false); // fecha a sidebar mobile ao selecionar jogo
  };

  const viewComponents = {
    chat: <VirtualAssistantChat selectedMatch={selectedMatch} />,
    dashboard: <VirtualAssistantDashboard selectedMatch={selectedMatch} />,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full flex flex-col space-y-4"
    >
      {/* Header */}
      <div className="text-left w-full">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-light text-white tracking-tight">
          Bem-Vindo(a) ao{" "}
          <span className="font-bold text-brand-yellow">Assistente Virtual</span>
        </h1>
        {selectedMatch && (
          <p className="text-slate-400 text-sm mt-1.5">
            Analisando:{" "}
            <span className="text-white font-medium">
              {selectedMatch.home_team} {selectedMatch.score || "0-0"}{" "}
              {selectedMatch.away_team}
            </span>
            {selectedMatch.time && (
              <span className="text-red-400 ml-2">• {selectedMatch.time}'</span>
            )}
          </p>
        )}
      </div>

      {/* ── Botão de Jogos ao vivo (mobile only) ── */}
      <div className="lg:hidden">
        <button
          onClick={() => setSidebarOpen((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm font-medium hover:border-brand-yellow/40 transition-all"
        >
          <span className="flex items-center gap-2">
            <Tv2 size={16} className="text-brand-yellow" />
            {selectedMatch
              ? `${selectedMatch.home_team} × ${selectedMatch.away_team}`
              : "Jogos ao vivo & Funções"}
          </span>
          {sidebarOpen ? (
            <ChevronUp size={16} className="text-slate-400" />
          ) : (
            <ChevronDown size={16} className="text-slate-400" />
          )}
        </button>

        {/* Sidebar colapsável mobile */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.22, ease: "easeInOut" }}
              className="overflow-hidden mt-2 bg-slate-900 border border-slate-800 rounded-2xl"
            >
              <div className="p-4">
                <VirtualAssistantSidebar
                  activeView={activeView}
                  setActiveView={(v) => {
                    setActiveView(v);
                    setSidebarOpen(false);
                  }}
                  onSelectMatch={handleSelectMatch}
                  selectedMatch={selectedMatch}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Layout Desktop: sidebar fixa à esquerda ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8">

        {/* Sidebar Desktop (hidden mobile) */}
        <div className="hidden lg:block lg:col-span-1 border-r border-slate-800 pr-6">
          <VirtualAssistantSidebar
            activeView={activeView}
            setActiveView={setActiveView}
            onSelectMatch={handleSelectMatch}
            selectedMatch={selectedMatch}
          />
        </div>

        {/* Chat / Dashboard — ocupa tudo no mobile, 3/4 no desktop */}
        <div className="col-span-1 lg:col-span-3 relative" style={{ minHeight: "calc(100vh - 18rem)" }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, x: activeView === "chat" ? -10 : 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: activeView === "chat" ? 10 : -10 }}
              transition={{ duration: 0.2 }}
              className="w-full h-full"
            >
              {viewComponents[activeView] || viewComponents.chat}
            </motion.div>
          </AnimatePresence>
        </div>

      </div>
    </motion.div>
  );
}
