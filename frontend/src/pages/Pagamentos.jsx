import { Copy, Receipt } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";

export default function Pagamentos() {
  const hashPix = "00020126580014br.gov.bcb.pix0136123e4567-e89b-12d3-a456-426655440000520400005303986540510.005802BR5913Central Pix6009SAO P...";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(hashPix);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col space-y-12 pb-12 pt-6">
      <div className="text-center mb-4">
        <h1 className="text-3xl md:text-5xl font-light text-white tracking-tight">
          Efetue o seu <span className="font-bold text-brand-yellow">Pagamento via Pix</span>
        </h1>
        <p className="text-slate-400 mt-4 max-w-lg mx-auto">
          Praticidade e rapidez em um ecossistema inteiramente seguro. O seu saldo ficará disponível em meros segundos logo após a transação eletrônica.
        </p>
      </div>

      <div className="w-full max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-0 lg:divide-x divide-slate-700/50 bg-slate-800/30 p-8 md:p-12 rounded-[2rem] border border-slate-700 shadow-2xl">
        
        {/* Lado Esquerdo: Input de Copy-Paste Escuro */}
        <div className="flex flex-col justify-center items-center lg:items-start lg:pr-12 text-center lg:text-left space-y-6">
          <div className="bg-slate-800 w-16 h-16 rounded-full flex items-center justify-center shadow-inner border border-slate-700">
            <Receipt size={32} className="text-brand-yellow" />
          </div>
          
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-white tracking-tight">Pix Copia e Cola</h2>
            <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
              Copie o código de pagamento abaixo e execute a transação dentro do aplicativo da sua carteira ou banco base.
            </p>
          </div>

          <div className="w-full relative mt-2">
            <div className="bg-slate-950 border border-slate-700 rounded-xl p-4 pr-16 break-all text-xs font-mono text-slate-300 shadow-inner select-all min-h-[60px] flex items-center">
              {hashPix}
            </div>
            
            <button 
              onClick={handleCopy}
              className="absolute right-2 top-0 bottom-0 my-auto h-10 px-4 flex items-center justify-center bg-brand-yellow hover:bg-yellow-400 text-slate-900 rounded-lg transition-all shadow-md active:scale-95 font-bold text-sm tracking-wide gap-2"
            >
              {copied ? "COPIADO!" : <span><Copy size={16} /></span>}
            </button>
          </div>
        </div>

        {/* Lado Direita: Cartão Branco "Puro Claro" QR Code */}
        <div className="flex flex-col justify-center items-center lg:pl-12">
          <p className="text-slate-400 font-bold mb-6 text-sm uppercase tracking-widest text-center">
            Ou escaneie diretamente
          </p>
          
          <motion.div 
            whileHover={{ scale: 1.02 }}
            className="bg-white p-8 md:p-10 rounded-[2rem] shadow-2xl flex flex-col items-center justify-center space-y-8 transition-transform w-full max-w-[320px]"
          >
            {/* Simulated QR Code Interface */}
            <div className="w-[200px] h-[200px] bg-slate-50 flex items-center justify-center border-[8px] border-slate-900 rounded-2xl relative overflow-hidden shadow-inner">
              
              {/* Complex Generic Blocks pattern */}
              <div className="absolute inset-0 grid grid-cols-5 grid-rows-5 gap-1.5 p-3 opacity-90">
                 {[...Array(25)].map((_, i) => (
                    <div key={i} className={`bg-slate-900 rounded-sm ${Math.random() > 0.3 ? 'opacity-100' : 'opacity-0'}`}></div>
                 ))}
              </div>
              
              {/* Middle Label of the QR simulated visual */}
              <div className="absolute bg-white p-2 rounded-xl shadow-lg z-10 w-16 h-16 flex items-center justify-center border-2 border-slate-100">
                <span className="font-extrabold text-xs text-slate-900 leading-tight text-center">
                  Pix<br/><span className="text-brand-yellow">App</span>
                </span>
              </div>
            </div>

            <div className="text-center w-full">
               <div className="h-px w-full bg-slate-200 my-4"></div>
               <p className="text-slate-900 font-extrabold text-2xl tracking-tight">R$ 30,90</p>
               <p className="text-slate-500 font-bold text-[10px] uppercase tracking-widest pt-2">Validade da Chave: 30 minutos</p>
            </div>
          </motion.div>
        </div>

      </div>
    </div>
  );
}
