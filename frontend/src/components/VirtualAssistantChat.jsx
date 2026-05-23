import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Zap, Info, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { predictMatch, predictShot, getLiveMatchDetail, chatBetina, simulateWhatIf } from "../services/api";
import SimulatorCard from "./SimulatorCard";

const BASE_MATCH = { home_score: 0, away_score: 0, minute: 60, home_xg: 1.0, away_xg: 0.8, xg_diff: 0.2, home_shots: 10, away_shots: 8, home_shots_ot: 4, away_shots_ot: 3, home_pass_acc: 0.8, away_pass_acc: 0.75, pressure_ratio: 1.1, home_passes: 300, away_passes: 280, home_pressures: 80, away_pressures: 90, home_fouls: 10, away_fouls: 10 };
const BASE_SHOT = { distance_to_goal: 15, angle_to_goal: 30, xg: 0.1, under_pressure: 1, first_time: 0, open_goal: 0, minute: 60, score_diff: 0, is_home_team: 1, technique: "Normal", body_part: "Right Foot", shot_type: "Open Play", time_seconds: 3600, is_second_half: 1, is_extra_time: 0 };
const BASE_FOUL = { x: 70, y: 40, dist_to_center: 20, in_danger_zone: 0, in_final_third: 1, minute: 60, under_pressure: 1, score_diff: 0, team_losing: 0, is_home_team: 1, foul_type: "Regular", advantage: 0, time_seconds: 3600, is_second_half: 1 };

/**
 * VirtualAssistantChat — Chat inteligente conectado ao backend.
 *
 * Comportamento:
 * - Quando o usuário seleciona um jogo ao vivo, o assistente carrega
 *   automaticamente os dados do jogo e faz uma análise inicial.
 * - O usuário pode perguntar coisas e o assistente consulta os modelos
 *   do backend para responder com narrativas SHAP explicadas.
 * - Respostas são amigáveis e explicam o "porquê", não apenas dados brutos.
 */

// Mensagem de boas-vindas padrão
const WELCOME_MSG = {
  id: "welcome",
  sender: "agent",
  text: "Olá! Eu sou a **Elli AI**, sua assistente de análise esportiva. 🏟️\n\nSelecione um jogo ao vivo na barra lateral para eu analisar, ou me pergunte qualquer coisa sobre apostas esportivas!",
  type: "text",
};

export default function VirtualAssistantChat({ selectedMatch }) {
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [inputVal, setInputVal] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const prevMatchIdRef = useRef(null);
  const lastPredictionRef = useRef(null); // Guarda última predição para contexto do chat

  // ID de sessão único para manter histórico Gemini — gerado uma vez por montagem
  const sessionIdRef = useRef(`session_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`);

  // Auto-scroll para última mensagem
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Quando um jogo ao vivo é selecionado → análise automática
  useEffect(() => {
    if (!selectedMatch || selectedMatch.event_id === prevMatchIdRef.current) return;
    prevMatchIdRef.current = selectedMatch.event_id;
    analyzeMatch(selectedMatch);
  }, [selectedMatch]);

  // ─── Análise Automática de Jogo Ao Vivo ────────────────────────────────
  async function analyzeMatch(match) {
    const userMsg = {
      id: Date.now(),
      sender: "system",
      text: `📺 Jogo selecionado: **${match.home_team} ${match.score || "0-0"} ${match.away_team}** (${match.time ? match.time + "'" : "Ao Vivo"})`,
      type: "system",
    };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      // Tenta buscar detalhes + odds do jogo
      let detail = null;
      try {
        detail = await getLiveMatchDetail(match.event_id);
      } catch {
        // Se falhar, segue com dados básicos
      }

      // Monta dados para predição de resultado
      const score = (match.score || "0-0").split("-").map(Number);
      const homeScore = score[0] || 0;
      const awayScore = score[1] || 0;
      const minute = parseInt(match.time) || 45;

      // Dados estimados para predição (sem estatísticas detalhadas reais,
      // usamos estimativas razoáveis baseadas no placar)
      // IMPORTANTE: campos int no schema (shots, passes, pressures, fouls) devem ser inteiros
      const matchData = {
        home_team_name: match.home_team || "Mandante",
        away_team_name: match.away_team || "Visitante",
        home_score: homeScore,
        away_score: awayScore,
        minute: minute,
        home_xg: homeScore * 1.1 + 0.3,
        away_xg: awayScore * 1.1 + 0.3,
        xg_diff: (homeScore - awayScore) * 1.1,
        home_shots: Math.floor(Math.max(homeScore * 4, 3)),
        away_shots: Math.floor(Math.max(awayScore * 4, 3)),
        home_shots_ot: Math.floor(Math.max(homeScore * 2, 1)),
        away_shots_ot: Math.floor(Math.max(awayScore * 2, 1)),
        home_passes: Math.floor(250 + Math.random() * 200),
        away_passes: Math.floor(250 + Math.random() * 200),
        home_pass_acc: +(0.75 + Math.random() * 0.15).toFixed(2),
        away_pass_acc: +(0.75 + Math.random() * 0.15).toFixed(2),
        home_pressures: Math.floor(50 + Math.random() * 80),
        away_pressures: Math.floor(50 + Math.random() * 80),
        pressure_ratio: +(0.8 + Math.random() * 0.8).toFixed(2),
        home_fouls: Math.floor(5 + Math.random() * 10),
        away_fouls: Math.floor(5 + Math.random() * 10),
      };

      const prediction = await predictMatch(matchData);
      lastPredictionRef.current = prediction; // salva para contexto do chat

      // Monta a narrativa base do backend
      let response = prediction.narrative;

      // ── Bloco de Odds ────────────────────────────────────────────────
      const hp = prediction.home_win_probability;
      const dp = prediction.draw_probability;
      const ap = prediction.away_win_probability;

      // Odds justas calculadas a partir da probabilidade do modelo (1/prob)
      const fairHome = hp > 0 ? (1 / hp).toFixed(2) : "-";
      const fairDraw = dp > 0 ? (1 / dp).toFixed(2) : "-";
      const fairAway = ap > 0 ? (1 / ap).toFixed(2) : "-";

      // Tenta usar odds reais da BetsAPI (detail), senão mostra as justas
      let oddsBlock = "";
      let realOdds = null;
      if (detail && detail.odds) {
        // BetsAPI retorna odds em formato variado — tenta extrair 1x2
        const market = detail.odds["1_1"] || detail.odds["match_winner"] || null;
        if (market && typeof market === "object") {
          // BetsAPI odds format: { "home_od": "1.50", "draw_od": "3.20", "away_od": "5.00" }
          // ou array com bookmakers
          const firstBook = Array.isArray(market) ? market[0] : market;
          if (firstBook) {
            realOdds = {
              home: firstBook.home_od || firstBook["1"] || null,
              draw: firstBook.draw_od || firstBook["X"] || null,
              away: firstBook.away_od || firstBook["2"] || null,
              bookmaker: firstBook.bookmaker_name || firstBook.company_name || "Mercado",
            };
          }
        }
      }

      if (realOdds && realOdds.home) {
        // Compara odds reais com as justas do modelo
        const homeVal = parseFloat(realOdds.home) > parseFloat(fairHome);
        const awayVal = parseFloat(realOdds.away) > parseFloat(fairAway);
        const valueTag = homeVal
          ? `Possível valor em **${match.home_team}** — odd de mercado (${realOdds.home}) acima da justa (${fairHome}).`
          : awayVal
            ? `Possível valor em **${match.away_team}** — odd de mercado (${realOdds.away}) acima da justa (${fairAway}).`
            : "As odds do mercado estão alinhadas com o modelo — sem valor aparente no momento.";

        oddsBlock = (
          `\n\n📈 **Comparativo de Odds** (${realOdds.bookmaker})\n\n` +
          `⚽ **${match.home_team}**: ${realOdds.home} (justa: ${fairHome})\n` +
          `⚖️ **Empate**: ${realOdds.draw || "-"} (justa: ${fairDraw})\n` +
          `⚽ **${match.away_team}**: ${realOdds.away} (justa: ${fairAway})\n\n` +
          `🔎 ${valueTag}`
        );
      } else {
        // Sem odds reais — mostra odds justas do modelo
        oddsBlock = (
          `\n\n📈 **Odds Justas (calculadas pelo modelo)**\n\n` +
          `⚽ **${match.home_team}**: ${fairHome}\n` +
          `⚖️ **Empate**: ${fairDraw}\n` +
          `⚽ **${match.away_team}**: ${fairAway}\n\n` +
          `🔎 Compare com as odds da sua casa de apostas — se a odd oferecida for **maior** que a justa, pode haver valor!`
        );
      }

      response += oddsBlock;

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: "agent",
        text: response,
        type: "analysis",
        data: prediction,
      }, {
        id: Date.now() + 2,
        sender: "agent",
        text: "Deseja testar cenários hipotéticos ('E Se?') para essa partida?",
        type: "simulation_menu",
        options: [
           { label: "⚽ Simular Gol", target: "shot_step_1" },
           { label: "🟨 Simular Falta (Cartão)", target: "foul_step_1" },
           { label: "🏆 Mudar Resultados da Partida", target: "match_step_1" }
        ]
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: "agent",
        text: `⚠️ Não consegui analisar esse jogo no momento: ${err.message}\n\nVerifique se o backend está rodando com os modelos carregados.`,
        type: "error",
      }]);
    } finally {
      setIsTyping(false);
    }
  }

  // ─── Envio de Mensagem do Usuário (via Gemini) ─────────────────────────
  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputVal.trim() || isTyping) return;

    const userText = inputVal.trim();
    setInputVal("");

    setMessages(prev => [...prev, {
      id: Date.now(),
      sender: "user",
      text: userText,
      type: "text",
    }]);

    setIsTyping(true);

    try {
      // Monta contexto do jogo selecionado para injetar no prompt Gemini
      const matchContext = selectedMatch ? {
        home_team: selectedMatch.home_team,
        away_team: selectedMatch.away_team,
        score: selectedMatch.score,
        time: selectedMatch.time,
        league: selectedMatch.league,
        prediction: lastPredictionRef.current,
      } : null;

      const data = await chatBetina({
        session_id: sessionIdRef.current,
        message: userText,
        match_context: matchContext,
      });

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: "agent",
        text: data.response,
        type: "text",
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: "agent",
        text: `Ops, tive um problema ao processar sua mensagem. Tente novamente! 😅`,
        type: "error",
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  // ─── Lógica Interativa de Botões (E Se) ─────────────────────────────────
  function handleSimButton(opt) {
    if (opt.target === "shot_step_1" || opt.target === "foul_step_1" || opt.target === "match_step_1") {
       const coreType = opt.target.split("_")[0];
       const typeNames = { shot: "Chute → Gol", foul: "Falta → Cartão", match: "Resultado" };

       // Passo 1: Seleção de time
       setMessages(prev => [...prev,
         { id: Date.now(), sender: "user", text: opt.label, type: "text" },
         { id: Date.now()+1, sender: "agent", text: `Para qual time você quer direcionar a simulação de **${typeNames[coreType]}**?`, type: "simulation_menu",
           options: [
             { label: selectedMatch?.home_team || "Mandante", target: `${coreType}_open_card`, isHomeRef: 1 },
             { label: selectedMatch?.away_team || "Visitante", target: `${coreType}_open_card`, isHomeRef: 0 }
           ]
         }
       ]);

    } else if (opt.target && opt.target.endsWith("_open_card")) {
       // Passo 2: Injeta o SimulatorCard visual diretamente no chat
       const coreType = opt.target.split("_")[0];
       const isHome = opt.isHomeRef;

       setMessages(prev => [...prev,
         { id: Date.now(), sender: "user", text: opt.label, type: "text" },
         { id: Date.now()+1, sender: "agent", text: "", type: "simulator_card",
           simType: coreType, isHome: isHome }
       ]);
    }
  }

  // runInteractiveSimulation removido — agora o SimulatorCard faz tudo inline

  // ─── Renderização de Mensagem ──────────────────────────────────────────
  function renderMessage(msg) {
    const isUser = msg.sender === "user";
    const isSystem = msg.sender === "system";

    if (isSystem) {
      return (
        <div className="flex justify-center">
          <div className="bg-slate-700/50 text-slate-300 text-xs px-4 py-2 rounded-full border border-slate-600">
            {renderMarkdown(msg.text)}
          </div>
        </div>
      );
    }

    // SimulatorCard renderizado em largura total (fora da bolha)
    if (msg.type === "simulator_card") {
      return (
        <div className="w-full">
          <SimulatorCard simType={msg.simType} isHome={msg.isHome} selectedMatch={selectedMatch} />
        </div>
      );
    }

    return (
      // Elli → esquerda (justify-start) | Usuário → direita (justify-end)
      <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
        {/* Avatar da Elli AI */}
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-yellow to-yellow-600 flex-shrink-0 flex items-center justify-center mr-2 mt-1 shadow-md">
            <span className="text-slate-900 text-xs font-bold">E</span>
          </div>
        )}
        <div
          className={`max-w-[82%] md:max-w-[72%] p-4 text-[14px] leading-relaxed shadow-lg ${
            isUser
              ? "bg-brand-yellow text-slate-900 rounded-2xl rounded-br-sm"
              : msg.type === "error"
                ? "bg-red-900/40 text-red-200 rounded-2xl rounded-bl-sm border border-red-700/30"
                : msg.type === "analysis" || msg.type === "simulation_menu"
                  ? "bg-slate-700/80 text-slate-100 rounded-2xl rounded-bl-sm border border-slate-600/50"
                  : "bg-slate-700/80 text-slate-100 rounded-2xl rounded-bl-sm border border-slate-600/50"
          }`}
        >
          {renderMarkdown(msg.text)}

          {/* Menus Interativos de Botões */}
          {msg.type === "simulation_menu" && msg.options && (
            <div className="mt-4 flex flex-col gap-2 border-t border-slate-600/50 pt-4">
              {msg.options.map((opt, i) => (
                <button 
                  key={i} 
                  onClick={() => handleSimButton(opt)}
                  className="bg-slate-800 border border-brand-yellow/30 hover:bg-brand-yellow/20 hover:border-brand-yellow text-brand-yellow font-medium text-[13px] px-4 py-2.5 rounded-xl text-left transition-all active:scale-95 flex items-center gap-2"
                >
                  <span className="flex-1">{opt.label}</span>
                  <ArrowRight size={14} className="opacity-50" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ─── Markdown: negrito + parágrafos + quebras de linha ────────────────
  function renderMarkdown(text) {
    // Divide em parágrafos (dupla quebra de linha)
    const paragraphs = text.split(/\n{2,}/);
    return (
      <span className="block space-y-3">
        {paragraphs.map((para, pi) => {
          // Dentro de cada parágrafo, processa negrito e quebras simples
          const lines = para.split("\n");
          return (
            <span key={pi} className="block">
              {lines.map((line, li) => {
                const parts = line.split(/(\*\*[^*]+\*\*)/g);
                return (
                  <span key={li} className="block">
                    {parts.map((part, i) =>
                      part.startsWith("**") && part.endsWith("**") ? (
                        <strong key={i}>{part.slice(2, -2)}</strong>
                      ) : (
                        <span key={i}>{part}</span>
                      )
                    )}
                  </span>
                );
              })}
            </span>
          );
        })}
      </span>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-14rem)] bg-slate-800/30 rounded-2xl border border-slate-700 overflow-hidden shadow-2xl">
      {/* Header do Chat */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700 bg-slate-800/90 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-brand-yellow to-yellow-600 overflow-hidden flex-shrink-0 border-2 border-brand-yellow shadow-sm flex items-center justify-center">
            <Zap size={24} className="text-slate-900" />
          </div>
          <div>
            <h2 className="text-white font-bold text-base">Elli AI</h2>
            <p className="text-green-400 text-xs flex items-center font-medium">
              <span className="w-2 h-2 rounded-full bg-green-400 mr-2 animate-pulse shadow-[0_0_8px_rgba(74,222,128,0.8)]" />
              {selectedMatch ? `Analisando • ${selectedMatch.home_team} vs ${selectedMatch.away_team}` : "Online"}
            </p>
          </div>
        </div>
        {selectedMatch && (
          <div className="hidden sm:flex items-center gap-2">
            <span className="px-2.5 py-1 bg-red-600 text-white text-[10px] font-bold rounded-full flex items-center gap-1 uppercase">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              {selectedMatch.time ? `${selectedMatch.time}'` : "Live"}
            </span>
            <span className="text-white font-bold text-sm">{selectedMatch.score || "0-0"}</span>
          </div>
        )}
      </div>

      {/* Mensagens */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 15, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ type: "spring", stiffness: 220, damping: 20 }}
            >
              {renderMessage(msg)}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Indicador de digitando */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-end"
          >
            <div className="bg-brand-yellow/20 text-brand-yellow px-4 py-3 rounded-2xl rounded-br-sm flex items-center gap-2 border border-brand-yellow/20">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm font-medium">Elli está analisando...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-slate-900/40 backdrop-blur border-t border-slate-800 shrink-0">
        <form
          onSubmit={handleSend}
          className="flex items-center bg-slate-900 rounded-full border border-slate-700 px-3 py-2 shadow-inner"
        >
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder={selectedMatch
              ? `Pergunte sobre ${selectedMatch.home_team} vs ${selectedMatch.away_team}...`
              : "Selecione um jogo ou pergunte algo..."
            }
            disabled={isTyping}
            className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 px-3 py-2 outline-none text-sm min-w-0 disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={!inputVal.trim() || isTyping}
            className="p-2.5 bg-brand-yellow hover:bg-yellow-400 text-slate-900 rounded-full transition-colors flex items-center justify-center ml-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} className="translate-x-[1px]" />
          </button>
        </form>
      </div>
    </div>
  );
}
