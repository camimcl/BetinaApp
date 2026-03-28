import { Trophy, ChevronRight, Settings, Lock, Activity, Star } from "lucide-react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

// Modulo Componente de Item Customizável
function ProfileMenuItem({ icon, label, onClick }) {
  return (
    <motion.button 
      onClick={onClick}
      whileHover={{ scale: 1.015 }}
      whileTap={{ scale: 0.99 }}
      className="w-full flex items-center justify-between bg-slate-800/40 hover:bg-slate-800 transition-colors border border-slate-700/60 rounded-xl p-4 md:p-5 group shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-yellow/50"
    >
      <div className="flex items-center space-x-4">
        <div className="text-slate-400 group-hover:text-brand-yellow transition-colors">
          {icon}
        </div>
        <span className="text-white font-medium text-[15px]">{label}</span>
      </div>
      <ChevronRight size={20} className="text-slate-500 group-hover:text-white transition-colors" />
    </motion.button>
  );
}

export default function Perfil() {
  const navigate = useNavigate();

  const menuOptions = [
    { label: "Seus Jogos Favoritados", icon: <Star size={20} />, action: () => navigate('/jogos') },
    { label: "Trocar senha", icon: <Lock size={20} />, action: () => {} },
    { label: "Meus Desempenhos", icon: <Activity size={20} />, action: () => navigate('/assistente') },
    { label: "Configurações Globais", icon: <Settings size={20} />, action: () => {} },
  ];

  return (
    <div className="flex flex-col items-center mt-6 lg:mt-10 w-full max-w-2xl mx-auto pb-16">
      
      {/* Cabeçalho do Perfil (Avatar + Informações) */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center text-center space-y-6"
      >
        <div className="relative">
          {/* Avatar com Bordas Arredondadas Simétricas */}
          <div className="w-32 h-32 md:w-36 md:h-36 rounded-full border-[6px] border-slate-800 bg-slate-900 flex items-center justify-center overflow-hidden shadow-2xl relative z-10">
             <img 
               src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=200&h=200" 
               alt="Perfil Avatar Kaillany" 
               className="w-full h-full object-cover"
             />
          </div>
          
          {/* Simulação Fictícia do Halo Fundo Roxo nas opções */}
          <div className="absolute inset-0 bg-purple-600/20 blur-2xl rounded-full w-[150%] h-[150%] -left-1/4 -top-1/4 z-0 pointer-events-none"></div>

          {/* Badge Online Hover */}
          <div className="absolute bottom-2 right-4 md:bottom-3 md:right-5 w-5 h-5 bg-green-500 rounded-full border-4 border-slate-900 shadow-md z-20"></div>
        </div>

        <div className="relative z-10">
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Olá, <span className="text-brand-yellow">Kaillany Francinny!</span>
          </h1>
          
          {/* Tag Central Jogadora Grátis */}
          <div className="flex items-center justify-center gap-2 mt-4 bg-slate-800/80 border border-slate-700 py-1.5 px-4 rounded-full w-max mx-auto shadow-inner">
            <Trophy size={16} className="text-brand-yellow fill-brand-yellow drop-shadow-md" />
            <span className="text-slate-200 text-xs font-bold uppercase tracking-widest pt-px">Jogadora Grátis</span>
          </div>
        </div>
      </motion.div>

      {/* Traço Limitador Horizontal */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent my-10 max-w-sm"></div>

      {/* Lista de Navegação Flexível */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex flex-col gap-3.5 w-full max-w-lg px-4"
      >
        {menuOptions.map((option, idx) => (
          <ProfileMenuItem key={idx} icon={option.icon} label={option.label} onClick={option.action} />
        ))}
      </motion.div>

    </div>
  );
}
