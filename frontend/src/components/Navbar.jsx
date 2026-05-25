import { useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { Search, Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  const navLinks = [
    { name: "Home", path: "/" },
    { name: "Assistente Virtual", path: "/assistente" },
    { name: "Jogos", path: "/jogos" },
    { name: "Pagamentos", path: "/pagamentos" },
    { name: "Perfil", path: "/perfil" },
  ];

  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors ${
      isActive ? "text-brand-yellow" : "text-slate-300 hover:text-white"
    }`;

  return (
    <nav className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 md:h-20">

          {/* Logo */}
          <div className="flex-shrink-0 flex items-center">
            <Link to="/" className="text-2xl font-bold text-white tracking-tighter">
              Intelli<span className="text-brand-yellow">Bet</span>
            </Link>
          </div>

          {/* Links Desktop */}
          <div className="hidden lg:flex space-x-8">
            {navLinks.map((link) => (
              <NavLink key={link.name} to={link.path} className={linkClass}>
                {link.name}
              </NavLink>
            ))}
          </div>

          {/* Search + CTA Desktop */}
          <div className="hidden md:flex items-center space-x-4">
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
            <button className="bg-brand-yellow hover:bg-yellow-400 text-slate-900 px-5 py-2 rounded-lg font-bold transition-colors text-sm whitespace-nowrap">
              Encontre Mais
            </button>
          </div>

          {/* Botão Hamburguer Mobile */}
          <button
            className="md:hidden p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Menu"
          >
            {menuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

        </div>
      </div>

      {/* Menu Mobile — dropdown deslizante */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="md:hidden overflow-hidden bg-slate-900 border-t border-slate-800"
          >
            <div className="px-4 pt-3 pb-5 space-y-1">
              {navLinks.map((link) => (
                <NavLink
                  key={link.name}
                  to={link.path}
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center w-full px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? "bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/20"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white"
                    }`
                  }
                >
                  {link.name}
                </NavLink>
              ))}

              {/* Search mobile */}
              <div className="pt-3 border-t border-slate-800 mt-2">
                <div className="relative mb-3">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-slate-400" />
                  </div>
                  <input
                    type="text"
                    className="block w-full pl-10 pr-3 py-2.5 border border-slate-700 rounded-xl bg-slate-800 text-slate-300 placeholder-slate-400 focus:outline-none focus:border-brand-yellow text-sm"
                    placeholder="Pesquise jogos, times..."
                  />
                </div>
                <button className="w-full bg-brand-yellow hover:bg-yellow-400 text-slate-900 py-3 rounded-xl font-bold transition-colors text-sm">
                  Encontre Mais
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
