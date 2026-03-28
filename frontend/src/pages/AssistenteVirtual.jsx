import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import VirtualAssistantSidebar from "../components/VirtualAssistantSidebar";
import VirtualAssistantChat from "../components/VirtualAssistantChat";
import VirtualAssistantDashboard from "../components/VirtualAssistantDashboard";
import { motion, AnimatePresence } from "framer-motion";

export default function AssistenteVirtual() {
  const [activeView, setActiveView] = useState('chat');
  const [selectedMatch, setSelectedMatch] = useState(null);
  const location = useLocation();

  // Se veio da página de Jogos com um jogo selecionado
  useEffect(() => {
    if (location.state?.selectedMatch) {
      setSelectedMatch(location.state.selectedMatch);
      setActiveView('chat'); // vai direto pro chat para analisar
    }
  }, [location.state]);

  const handleSelectMatch = (match) => {
    setSelectedMatch(match);
    if (activeView !== 'chat') {
      setActiveView('chat'); // switch to chat to show analysis
    }
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
      className="w-full flex flex-col space-y-6"
    >
      {/* Header */}
      <div className="text-left w-full mb-2">
        <h1 className="text-3xl lg:text-4xl font-light text-white tracking-tight">
          Bem-Vindo(a) ao <span className="font-bold text-brand-yellow">Assistente Virtual</span>
        </h1>
        {selectedMatch && (
          <p className="text-slate-400 text-sm mt-2">
            Analisando: <span className="text-white font-medium">{selectedMatch.home_team} {selectedMatch.score || "0-0"} {selectedMatch.away_team}</span>
            {selectedMatch.time && <span className="text-red-400 ml-2">• {selectedMatch.time}'</span>}
          </p>
        )}
      </div>

      {/* Layout Split */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8">

        {/* Esquerda: Menu + Jogos */}
        <div className="lg:col-span-1 border-r-0 lg:border-r border-slate-800 lg:pr-6">
          <VirtualAssistantSidebar
            activeView={activeView}
            setActiveView={setActiveView}
            onSelectMatch={handleSelectMatch}
            selectedMatch={selectedMatch}
          />
        </div>

        {/* Direita: Chat / Dashboard / Simulation */}
        <div className="lg:col-span-3 relative h-[calc(100vh-14rem)]">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, x: activeView === 'chat' ? -10 : 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: activeView === 'chat' ? 10 : -10 }}
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
