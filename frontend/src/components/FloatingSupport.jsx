import { Send } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

const TELEGRAM_BOT_URL = "https://t.me/betina_app_bot?start=site";

export default function FloatingSupport() {
  const [showBubble, setShowBubble] = useState(false);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowBubble(true), 3000);
    return () => clearTimeout(timer);
  }, []);

  function handleTelegramClick() {
    setShowModal(true);
    setShowBubble(false);
  }

  function confirmTelegram() {
    setShowModal(false);
    window.open(TELEGRAM_BOT_URL, "_blank", "noopener");
  }

  return (
    <>
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end space-y-3">
        
        {/* Balão de fala */}
        <AnimatePresence>
          {showBubble && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="absolute right-16 bottom-4 md:bottom-2 bg-slate-800 text-white text-sm px-4 py-3 rounded-2xl rounded-br-none shadow-2xl border border-slate-700 min-w-[200px]"
            >
              <p className="font-medium text-slate-200">
                Quer palpites em<br/>
                <strong className="text-brand-yellow">tempo real?</strong> 🎯
              </p>
              <div className="absolute -right-2 bottom-0 w-0 h-0 border-t-[10px] border-t-transparent border-l-[12px] border-l-slate-800 border-b-[8px] border-b-transparent drop-shadow-md"></div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Ícone Telegram */}
        <motion.button 
          onClick={handleTelegramClick}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          className="w-10 h-10 bg-[#229ED9] rounded-full flex items-center justify-center shadow-lg hover:shadow-[#229ED9]/30 transition-shadow text-white z-10 mr-1.5"
          title="Falar com a Elli AI no Telegram"
        >
          <Send size={18} className="fill-current -rotate-12" />
        </motion.button>

        {/* Avatar */}
        <motion.button
          onClick={handleTelegramClick}
          onMouseEnter={() => setShowBubble(true)}
          onMouseLeave={() => setShowBubble(false)}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="w-14 h-14 rounded-full bg-brand-yellow p-0.5 shadow-xl shadow-brand-yellow/20 relative z-10 flex items-center justify-center cursor-pointer"
        >
          <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center overflow-hidden border-2 border-brand-yellow">
             <img 
               src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=150&h=150" 
               alt="Elli AI" 
               className="w-full h-full object-cover"
             />
          </div>
        </motion.button>
      </div>

      {/* Modal de confirmação */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="bg-slate-800 border border-slate-700 rounded-3xl p-8 max-w-md w-full shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-full bg-[#229ED9] flex items-center justify-center shadow-lg">
                  <Send size={24} className="text-white fill-current -rotate-12" />
                </div>
                <div>
                  <h3 className="text-xl font-extrabold text-white">Elli AI</h3>
                  <p className="text-sm text-[#229ED9] font-bold">Telegram Bot</p>
                </div>
              </div>

              {/* Content */}
              <div className="space-y-4 mb-8">
                <p className="text-slate-300 text-[15px] leading-relaxed">
                  Ao abrir o Telegram, você poderá:
                </p>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <span className="text-brand-yellow text-lg mt-0.5">🎯</span>
                    <p className="text-slate-300 text-sm">Receber <strong className="text-white">palpites em tempo real</strong> com probabilidades e odds justas</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-brand-yellow text-lg mt-0.5">🔔</span>
                    <p className="text-slate-300 text-sm">Ativar <strong className="text-white">até 3 alertas diários</strong> com os melhores jogos do dia</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-brand-yellow text-lg mt-0.5">⚽</span>
                    <p className="text-slate-300 text-sm">Selecionar jogos ao vivo e <strong className="text-white">acompanhar análises detalhadas</strong></p>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-brand-yellow text-lg mt-0.5">💬</span>
                    <p className="text-slate-300 text-sm">Conversar direto com a <strong className="text-white">I.A. sobre qualquer partida</strong></p>
                  </div>
                </div>
              </div>

              {/* Buttons */}
              <div className="flex flex-col gap-3">
                <motion.button
                  onClick={confirmTelegram}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full bg-[#229ED9] hover:bg-[#1a8bc2] text-white font-extrabold py-4 rounded-xl shadow-lg shadow-[#229ED9]/20 transition-colors flex items-center justify-center gap-3 text-[15px]"
                >
                  <Send size={18} className="fill-current -rotate-12" />
                  Abrir Telegram e Conversar
                </motion.button>

                <button
                  onClick={() => setShowModal(false)}
                  className="w-full text-slate-400 hover:text-slate-300 font-medium py-3 text-sm transition-colors"
                >
                  Agora não
                </button>
              </div>

              <p className="text-center text-slate-500 text-xs mt-4">
                100% gratuito • Cancele alertas a qualquer momento
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
