import { Link, useNavigate } from "react-router-dom";
import AuthCard from "../components/AuthCard";

export default function Login() {
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    setTimeout(() => navigate('/'), 600);
  };

  return (
    <AuthCard className="max-w-md">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Login do Usuário</h1>
      </div>

      <form className="space-y-4" onSubmit={handleLogin}>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
          <input 
            type="email" 
            placeholder="Digite seu email" 
            className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Senha</label>
          <input 
            type="password" 
            placeholder="Digite sua senha" 
            className="w-full border border-slate-300 rounded-lg px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-yellow focus:border-transparent"
          />
        </div>

        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center">
            <input 
              type="checkbox" 
              className="h-4 w-4 text-brand-yellow border-slate-300 rounded focus:ring-brand-yellow accent-brand-yellow" 
            />
            <label className="ml-2 block text-sm text-slate-700">Manter conectado</label>
          </div>
          <Link to="#" className="text-sm font-medium text-red-500 hover:text-red-400 hover:underline">
            Esqueci minha senha
          </Link>
        </div>

        <button 
          type="submit"
          className="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 rounded-lg transition-colors mt-6"
        >
          Entrar
        </button>

        <p className="text-center text-sm text-slate-500 mt-4">
          Não tenho cadastro?{' '}
          <Link to="/cadastro" className="font-medium text-brand-yellow hover:text-yellow-500 hover:underline">
            Criar conta
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
