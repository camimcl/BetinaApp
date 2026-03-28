import { NavLink, Link } from "react-router-dom";
import { Search } from "lucide-react";

export default function Navbar() {
  const navLinks = [
    { name: "Home", path: "/" },
    { name: "Assistente Virtual", path: "/assistente" },
    { name: "Jogos", path: "/jogos" },
    { name: "Pagamentos", path: "/pagamentos" },
    { name: "Perfil", path: "/perfil" }
  ];

  return (
    <nav className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          
          {/* Logo / Brand */}
          <div className="flex-shrink-0 flex items-center">
            <Link to="/" className="text-2xl font-bold text-white tracking-tighter">
              Betina<span className="text-brand-yellow">App</span>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="hidden lg:flex space-x-8">
            {navLinks.map((link) => (
              <NavLink
                key={link.name}
                to={link.path}
                className={({ isActive }) =>
                  `text-sm font-medium transition-colors ${
                    isActive 
                      ? "text-brand-yellow" 
                      : "text-slate-300 hover:text-white"
                  }`
                }
              >
                {link.name}
              </NavLink>
            ))}
          </div>

          {/* Right Section: Search & CTA */}
          <div className="hidden md:flex items-center space-x-6">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-full leading-5 bg-slate-800 text-slate-300 placeholder-slate-400 focus:outline-none focus:bg-slate-700 focus:border-brand-yellow focus:ring-1 focus:ring-brand-yellow sm:text-sm transition-colors"
                placeholder="Pesquise"
              />
            </div>
            
            <button className="bg-brand-yellow hover:bg-yellow-400 text-slate-900 px-6 py-2 rounded-lg font-bold transition-colors">
              Encontre Mais
            </button>
          </div>

        </div>
      </div>
    </nav>
  );
}
