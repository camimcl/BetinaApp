import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col lg:flex-row min-h-[calc(100vh-10rem)] w-full items-center justify-between pb-8 pt-4">
      
      {/* Coluna Esquerda: Textos Hero */}
      <div className="w-full lg:w-[55%] flex flex-col space-y-8 z-10 pt-10 lg:pt-0">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-2 md:space-y-4"
        >
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold text-white leading-tight tracking-tighter drop-shadow-lg">
            <span className="text-rose-500">DESBLOQUEIE</span> GANHOS ILIMITADOS!
          </h1>
          <h2 className="text-2xl md:text-3xl lg:text-4xl font-black text-white leading-tight mt-2 drop-shadow-md tracking-tight uppercase">
            Participe do nosso <br className="hidden xl:block"/> programa exclusivo de <br className="hidden xl:block"/>
            <span className="text-brand-yellow text-4xl lg:text-5xl border-b-4 border-brand-yellow/30 pb-1 inline-block mt-2">Bets Online!</span>
          </h2>
        </motion.div>

        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="text-slate-400 text-base md:text-lg max-w-lg leading-relaxed font-medium"
        >
          Descubra uma nova forma de expandir agressivamente os seus ganhos utilizando nossa moderna tecnologia de I.A. 
          Junte-se a milhares de jogadores que já transformaram seu desempenho na principal plataforma esportiva.
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="flex flex-col sm:flex-row gap-4 lg:gap-6 pt-6"
        >
          <motion.button 
            onClick={() => navigate('/planos')}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="bg-brand-yellow hover:bg-yellow-400 text-slate-900 font-extrabold px-8 py-4 rounded-xl shadow-xl shadow-brand-yellow/20 transition-all w-full sm:w-auto text-lg uppercase tracking-wide border-2 border-transparent active:outline-none"
          >
            Saiba Mais
          </motion.button>
          
          <motion.button 
            onClick={() => window.open("https://t.me/betina_app_bot?start=site", "_blank", "noopener")}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="border-2 border-slate-600 bg-transparent text-white font-bold px-8 py-4 rounded-xl hover:bg-slate-800 transition-colors w-full sm:w-auto text-lg uppercase tracking-wide shadow-lg backdrop-blur-sm"
          >
            💬 Falar com a Betina
          </motion.button>
        </motion.div>
      </div>

      {/* Coluna Direita: Composição Visual */}
      <div className="w-full lg:w-[45%] flex justify-center lg:justify-end mt-16 lg:mt-0 relative h-[400px] md:h-[500px] lg:h-[650px]">
        {/* Placeholder mock-image for Athletes group integrating purely into background */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7 }}
          className="relative w-full h-full max-w-lg lg:max-w-xl rounded-[4rem] overflow-hidden shadow-2xl border-[6px] border-slate-800/80"
        >
          {/* Main Visual Image simulating Sports match momentum */}
          <img 
            src="https://images.unsplash.com/photo-1519766304817-4f37bda74a26?auto=format&fit=crop&q=80&w=800" 
            alt="Atletas Competindo" 
            className="w-full h-full object-cover opacity-80 mix-blend-screen scale-105"
          />
          {/* Deep Dark Gradients enveloping the border */}
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-slate-900/30"></div>
          <div className="absolute inset-0 bg-gradient-to-l from-slate-900/80 lg:from-slate-900/40 via-transparent to-transparent"></div>
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-slate-900/30"></div>
        </motion.div>
      </div>

    </div>
  );
}
