import { Check } from "lucide-react";
import { motion } from "framer-motion";

export default function Planos() {
  const plans = [
    {
      name: "Plano Entrada",
      price: "R$ 15,90 / Mês",
      recommended: false,
      features: [
        "Acesso à 5 simulações diárias",
        "Estatísticas básicas",
        "Suporte em horário comercial",
        "E-mails promocionais"
      ]
    },
    {
      name: "Plano Engajoso",
      price: "R$ 30,90 / Mês",
      recommended: true,
      features: [
        "Simulações ilimitadas",
        "Assistente virtual avançada (IA)",
        "Probabilidades em tempo real",
        "Gráficos avançados",
        "Suporte prioritário 24/7"
      ]
    },
    {
      name: "Plano VIP",
      price: "R$ 89,90 / Mês",
      recommended: false,
      features: [
        "Todos os recursos Engajoso",
        "Gestão de banca especializada",
        "Dicas preditivas assertivas",
        "Acesso a API",
        "Call mensal com grupo exclusivo"
      ]
    }
  ];

  return (
    <div className="flex flex-col space-y-12 pb-12 w-full pt-6">
      <div className="text-center">
        <h1 className="text-4xl md:text-5xl font-light text-white mb-4 tracking-tight">
          Nossos <span className="font-bold text-brand-yellow">Planos</span>
        </h1>
        <p className="text-slate-400 max-w-2xl mx-auto">
          Escolha a opção que mais se encaixa na sua estratégia de jogo. Cancele quando quiser, sem burocracia.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 items-stretch pt-4 max-w-6xl mx-auto px-4">
        {plans.map((plan, idx) => (
          <motion.div
            key={idx}
            whileHover={{ y: -8 }}
            transition={{ duration: 0.2 }}
            className={`relative flex flex-col bg-slate-800 rounded-[2rem] p-8 shadow-2xl ${
              plan.recommended ? "border-2 border-brand-yellow lg:scale-105 z-10 shadow-brand-yellow/10" : "border border-slate-700 mt-0 lg:mt-4"
            }`}
          >
            {plan.recommended && (
              <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <span className="bg-brand-yellow text-slate-900 text-xs font-bold uppercase tracking-widest py-1.5 px-6 rounded-full shadow-lg">
                  Mais Popular
                </span>
              </div>
            )}

            <div className="mb-6 border-b border-slate-700/60 pb-6 text-center">
              <h3 className={`text-xl font-bold mb-2 ${plan.recommended ? "text-brand-yellow" : "text-white"}`}>
                {plan.name}
              </h3>
              <p className="text-3xl font-bold text-white flex items-baseline justify-center">
                {plan.price.split(' ')[0]} 
                <span className="text-4xl mx-1">{plan.price.split(' ')[1]}</span>
                <span className="text-lg text-slate-400 font-normal"> {plan.price.split(' ').slice(2).join(' ')}</span>
              </p>
            </div>

            <ul className="flex-1 space-y-5 mb-8">
              {plan.features.map((feature, fIdx) => (
                <li key={fIdx} className="flex items-start">
                  <Check size={20} className="text-brand-yellow shrink-0 mr-3 mt-0.5" />
                  <span className="text-slate-300 text-[15px]">{feature}</span>
                </li>
              ))}
            </ul>

            <button 
              className={`w-full py-4 rounded-xl font-bold transition-all shadow-lg focus:ring-2 focus:ring-white focus:outline-none ${
                plan.recommended 
                  ? "bg-brand-yellow hover:bg-yellow-400 text-slate-900 shadow-brand-yellow/20 hover:shadow-brand-yellow/40 active:scale-95" 
                  : "bg-slate-700 hover:bg-slate-600 text-white active:scale-95"
              }`}
            >
              Assinar {plan.name}
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
