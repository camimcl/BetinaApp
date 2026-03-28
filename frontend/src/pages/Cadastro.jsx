import { Link, useNavigate } from "react-router-dom";
import AuthCard from "../components/AuthCard";

export default function Cadastro() {
  const navigate = useNavigate();

  const handleRegister = (e) => {
    e.preventDefault();
    setTimeout(() => navigate('/'), 600);
  };

  return (
    <AuthCard className="max-w-lg">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Cadastro de Usuário</h1>
      </div>

      <form className="space-y-4" onSubmit={handleRegister}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nome Completo</label>
            <input 
              type="text" 
              placeholder="Seu nome" 
              className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">CPF</label>
            <input 
              type="text" 
              placeholder="000.000.000-00" 
              className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Data de Nascimento</label>
            <input 
              type="date" 
              className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Telefone</label>
            <input 
              type="tel" 
              placeholder="(00) 00000-0000" 
              className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
          <input 
            type="email" 
            placeholder="seunome@email.com" 
            className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Senha</label>
          <input 
            type="password" 
            placeholder="••••••••" 
            className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
          />
        </div>

        <div className="space-y-2 mt-4">
          <div className="flex items-start">
            <input 
              type="checkbox" 
              className="mt-1 h-4 w-4 text-brand-yellow border-slate-300 rounded focus:ring-brand-yellow accent-brand-yellow" 
            />
            <label className="ml-2 block text-sm text-slate-600">
              Li e aceito o <Link to="#" className="text-brand-yellow hover:underline">Termo de Compromisso</Link>.
            </label>
          </div>
          <div className="flex items-start">
            <input 
              type="checkbox" 
              className="mt-1 h-4 w-4 text-brand-yellow border-slate-300 rounded focus:ring-brand-yellow accent-brand-yellow" 
            />
            <label className="ml-2 block text-sm text-slate-600">
              Quero receber Bônus e ofertas por email e SMS.
            </label>
          </div>
        </div>

        <button 
          type="submit"
          className="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 rounded-lg transition-colors mt-6"
        >
          Cadastrar
        </button>

        <p className="text-center text-sm text-slate-500 mt-4">
          Já possui conta?{' '}
          <Link to="/login" className="font-medium text-brand-yellow hover:text-yellow-500 hover:underline">
            Fazer login
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
