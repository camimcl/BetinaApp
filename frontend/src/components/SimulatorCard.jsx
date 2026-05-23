import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, RotateCcw, Trophy, TrendingUp, TrendingDown, Minus, ChevronDown } from "lucide-react";
import { simulateWhatIf } from "../services/api";

/* ═══════════════════════════════════════════════════════════════════════════
   CONSTANTES & HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */

const BASE_SHOT = {
  distance_to_goal: 18, angle_to_goal: 25, xg: 0.12, under_pressure: 1,
  first_time: 0, open_goal: 0, minute: 60, score_diff: 0, is_home_team: 1,
  technique: "Normal", body_part: "Right Foot", shot_type: "Open Play",
  time_seconds: 3600, is_second_half: 1, is_extra_time: 0,
};

const BASE_FOUL = {
  x: 75, y: 40, dist_to_center: 25, in_danger_zone: 0, in_final_third: 1,
  minute: 78, under_pressure: 1, score_diff: -1, team_losing: 1, is_home_team: 1,
  foul_type: "Regular", advantage: 0, time_seconds: 4680, is_second_half: 1,
  is_last_10_min: 0,
};

const BASE_MATCH = {
  home_score: 0, away_score: 0, minute: 60, home_xg: 1.0, away_xg: 0.8,
  xg_diff: 0.2, home_shots: 10, away_shots: 8, home_shots_ot: 4,
  away_shots_ot: 3, home_pass_acc: 0.8, away_pass_acc: 0.75,
  pressure_ratio: 1.1, home_passes: 300, away_passes: 280,
  home_pressures: 80, away_pressures: 90, home_fouls: 10, away_fouls: 10,
};

const PRESSURE_OPTIONS = [
  { value: 0, label: "Nenhuma", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  { value: 1, label: "Baixa", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  { value: 2, label: "Média", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  { value: 3, label: "Alta", color: "bg-red-500/20 text-red-400 border-red-500/30" },
];

const BODY_PARTS = [
  { value: "Right Foot", label: "Chute (pé direito)" },
  { value: "Left Foot", label: "Chute (pé esquerdo)" },
  { value: "Head", label: "Cabeceio" },
];

const FOUL_ZONES = [
  { id: "attack", label: "Ataque", icon: "⚔️", desc: "Terço final do adversário",
    overrides: { x: 90, y: 40, in_final_third: 1, in_danger_zone: 0, dist_to_center: 30 } },
  { id: "midfield", label: "Meio-campo", icon: "⚖️", desc: "Região central do campo",
    overrides: { x: 55, y: 40, in_final_third: 0, in_danger_zone: 0, dist_to_center: 15 } },
  { id: "defense", label: "Defesa", icon: "🛡️", desc: "Próximo da própria área",
    overrides: { x: 20, y: 40, in_final_third: 0, in_danger_zone: 1, dist_to_center: 5 } },
];

function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

/* ═══════════════════════════════════════════════════════════════════════════
   CAMPO DE FUTEBOL SVG — Componente interativo para chute e falta
   ═══════════════════════════════════════════════════════════════════════════ */

function FootballPitch({ position, onPositionChange, variant = "half", highlightZone = null }) {
  const svgRef = useRef(null);

  const handleClick = useCallback((e) => {
    if (!onPositionChange) return;
    const svg = svgRef.current;
    const rect = svg.getBoundingClientRect();
    const scaleX = 320 / rect.width;
    const scaleY = (variant === "full" ? 340 : 220) / rect.height;
    const rawX = (e.clientX - rect.left) * scaleX;
    const rawY = (e.clientY - rect.top) * scaleY;
    const cx = clamp(rawX, 20, 300);
    const cy = clamp(rawY, variant === "full" ? 20 : 30, variant === "full" ? 320 : 200);

    if (variant === "half") {
      // Calcula distância ao centro do gol (160, 12)
      const gx = 160, gy = 12;
      const pxDist = Math.sqrt((cx - gx) ** 2 + (cy - gy) ** 2);
      const dist = clamp(Math.round((pxDist / 190) * 40), 3, 45);
      // Ângulo visual ao gol
      const aL = Math.atan2(cy - 10, cx - 125);
      const aR = Math.atan2(cy - 10, cx - 195);
      const angle = clamp(Math.round(Math.abs(aR - aL) * (180 / Math.PI)), 3, 60);
      onPositionChange({ x: cx, y: cy, distance: dist, angle });
    } else {
      onPositionChange({ x: cx, y: cy });
    }
  }, [onPositionChange, variant]);

  const vbH = variant === "full" ? 340 : 220;

  return (
    <svg ref={svgRef} viewBox={`0 0 320 ${vbH}`} className="w-full cursor-crosshair rounded-xl overflow-hidden select-none" onClick={handleClick} style={{ maxHeight: variant === "full" ? 200 : 170 }}>
      <defs>
        <linearGradient id="pitchGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0d3320" />
          <stop offset="100%" stopColor="#1a4a30" />
        </linearGradient>
        <filter id="glow"><feGaussianBlur stdDeviation="3" result="g"/><feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="320" height={vbH} fill="url(#pitchGrad)" rx="12" />
      {/* Grass stripes */}
      {[0,1,2,3,4,5,6,7].map(i => <rect key={i} x="10" y={10 + i * ((vbH-20)/8)} width="300" height={(vbH-20)/16} fill="rgba(255,255,255,0.02)" />)}
      {/* Field outline */}
      <rect x="10" y="10" width="300" height={vbH - 20} fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="2" rx="2" />

      {variant === "half" ? (
        <>
          {/* Goal */}
          <rect x="125" y="3" width="70" height="10" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.6)" strokeWidth="2" rx="1" />
          {[130,140,150,160,170,180,190].map(lx => <line key={lx} x1={lx} y1="3" x2={lx} y2="13" stroke="rgba(255,255,255,0.15)" strokeWidth="0.5" />)}
          {/* Goal area */}
          <rect x="105" y="10" width="110" height="35" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          {/* Penalty area */}
          <rect x="55" y="10" width="210" height="80" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          {/* Penalty arc */}
          <path d="M 100 90 Q 160 115 220 90" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1.5" />
          {/* Penalty spot */}
          <circle cx="160" cy="65" r="2" fill="rgba(255,255,255,0.4)" />
          {/* Center arc */}
          <path d="M 10 210 Q 160 175 310 210" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1.5" />

          {/* Shot trajectory line */}
          {position && <line x1={position.x} y1={position.y} x2="160" y2="10" stroke="rgba(255,215,0,0.35)" strokeWidth="1.5" strokeDasharray="6,4" />}

          {/* Ball marker */}
          {position && (
            <g filter="url(#glow)">
              <circle cx={position.x} cy={position.y} r="14" fill="rgba(255,215,0,0.12)" />
              <circle cx={position.x} cy={position.y} r="8" fill="#FFD700" stroke="rgba(255,255,255,0.8)" strokeWidth="2" />
              <circle cx={position.x} cy={position.y} r="3" fill="rgba(26,26,46,0.6)" />
            </g>
          )}
        </>
      ) : (
        <>
          {/* Full field for fouls */}
          <line x1="10" y1={vbH/2} x2="310" y2={vbH/2} stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          <circle cx="160" cy={vbH/2} r="40" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />
          <circle cx="160" cy={vbH/2} r="3" fill="rgba(255,255,255,0.3)" />
          {/* Top penalty area */}
          <rect x="55" y="10" width="210" height="65" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          <rect x="105" y="10" width="110" height="30" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
          {/* Bottom penalty area */}
          <rect x="55" y={vbH-75} width="210" height="65" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          <rect x="105" y={vbH-40} width="110" height="30" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
          {/* Goals */}
          <rect x="130" y="3" width="60" height="8" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" rx="1" />
          <rect x="130" y={vbH-11} width="60" height="8" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" rx="1" />

          {/* Zone highlights */}
          {highlightZone === "attack" && <rect x="12" y="12" width="296" height={(vbH-24)/3} fill="rgba(255,215,0,0.08)" rx="4" />}
          {highlightZone === "midfield" && <rect x="12" y={12 + (vbH-24)/3} width="296" height={(vbH-24)/3} fill="rgba(255,215,0,0.08)" rx="4" />}
          {highlightZone === "defense" && <rect x="12" y={12 + 2*(vbH-24)/3} width="296" height={(vbH-24)/3} fill="rgba(255,215,0,0.08)" rx="4" />}

          {/* Ball marker */}
          {position && (
            <g filter="url(#glow)">
              <circle cx={position.x} cy={position.y} r="14" fill="rgba(255,215,0,0.12)" />
              <circle cx={position.x} cy={position.y} r="8" fill="#FFD700" stroke="rgba(255,255,255,0.8)" strokeWidth="2" />
              <circle cx={position.x} cy={position.y} r="3" fill="rgba(26,26,46,0.6)" />
            </g>
          )}
        </>
      )}
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   CONTROLES — Slider, Segmented, Toggle, Stepper
   ═══════════════════════════════════════════════════════════════════════════ */

function StyledSlider({ label, value, min, max, step = 1, unit = "", onChange, icon }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-xs font-medium flex items-center gap-1.5">
          {icon && <span className="text-sm">{icon}</span>}{label}
        </span>
        <span className="text-brand-yellow font-bold text-sm tabular-nums">{step < 1 ? value.toFixed(step < 0.1 ? 2 : 1) : value}{unit}</span>
      </div>
      <div className="relative">
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-brand-yellow/60 to-brand-yellow rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
        <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(parseFloat(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        />
      </div>
      <div className="flex justify-between text-[10px] text-slate-600">
        <span>{min}{unit}</span><span>{max}{unit}</span>
      </div>
    </div>
  );
}

function SegmentedControl({ label, options, value, onChange, icon }) {
  return (
    <div className="space-y-2">
      <span className="text-slate-400 text-xs font-medium flex items-center gap-1.5">
        {icon && <span className="text-sm">{icon}</span>}{label}
      </span>
      <div className="flex gap-1.5">
        {options.map(opt => (
          <button key={opt.value} onClick={() => onChange(opt.value)}
            className={`flex-1 px-2 py-2 rounded-lg text-xs font-bold transition-all border ${
              value === opt.value ? (opt.color || "bg-brand-yellow/20 text-brand-yellow border-brand-yellow/40") : "bg-slate-800 text-slate-500 border-slate-700 hover:border-slate-600"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ToggleSwitch({ label, value, onChange, icon }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400 text-xs font-medium flex items-center gap-1.5">
        {icon && <span className="text-sm">{icon}</span>}{label}
      </span>
      <button onClick={() => onChange(value ? 0 : 1)}
        className={`relative w-11 h-6 rounded-full transition-colors ${value ? "bg-brand-yellow" : "bg-slate-700"}`}
      >
        <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform ${value ? "translate-x-[22px]" : "translate-x-0.5"}`} />
      </button>
    </div>
  );
}

function StyledSelect({ label, options, value, onChange, icon }) {
  return (
    <div className="space-y-2">
      <span className="text-slate-400 text-xs font-medium flex items-center gap-1.5">
        {icon && <span className="text-sm">{icon}</span>}{label}
      </span>
      <div className="relative">
        <select value={value} onChange={e => onChange(e.target.value)}
          className="w-full bg-slate-800 text-white text-xs rounded-lg px-3 py-2.5 border border-slate-700 focus:outline-none focus:border-brand-yellow/50 appearance-none cursor-pointer"
        >
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
      </div>
    </div>
  );
}

function Stepper({ label, value, onChange, min = 0, max = 10, icon }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400 text-xs font-medium flex items-center gap-1.5">
        {icon && <span className="text-sm">{icon}</span>}{label}
      </span>
      <div className="flex items-center gap-1">
        <button onClick={() => onChange(Math.max(min, value - 1))}
          className="w-7 h-7 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm font-bold flex items-center justify-center transition-colors">−</button>
        <span className="w-8 text-center text-white font-bold text-sm tabular-nums">{value}</span>
        <button onClick={() => onChange(Math.min(max, value + 1))}
          className="w-7 h-7 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm font-bold flex items-center justify-center transition-colors">+</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   BARRA DE PROGRESSO CIRCULAR (para P(gol) / P(cartão))
   ═══════════════════════════════════════════════════════════════════════════ */

function ProbCircle({ pct, label, color = "#FFD700", size = 80 }) {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
        <circle cx="40" cy="40" r={radius} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset} transform="rotate(-90 40 40)"
          className="transition-all duration-700" />
        <text x="40" y="37" textAnchor="middle" fill="white" fontSize="18" fontWeight="bold" className="tabular-nums">{pct}%</text>
        <text x="40" y="52" textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="8">{label}</text>
      </svg>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   RESULTADO VISUAL — Comparação Cenário Real vs Simulado
   ═══════════════════════════════════════════════════════════════════════════ */

function SimulatorResult({ simType, base, simulated, delta, narrative, baseValues, overrideValues }) {
  const keys = Object.keys(delta || {});
  if (!keys.length) return null;

  const mainKey = keys[0];
  const basePct = Math.round((base?.[mainKey] || 0) * 100);
  const simPct = Math.round((simulated?.[mainKey] || 0) * 100);
  const deltaPct = Math.round((delta?.[mainKey] || 0) * 100);
  const isPositive = deltaPct > 0;
  const isZero = Math.abs(deltaPct) < 1;

  const labelMap = {
    goal_probability: "P(gol)",
    card_probability: "P(cartão)",
    home_win: "Vitória Casa",
    draw: "Empate",
    away_win: "Vitória Fora",
  };

  // Descrição amigável dos cenários
  const shotDesc = (vals) => {
    const dist = vals?.distance_to_goal || "?";
    const press = PRESSURE_OPTIONS.find(p => p.value === (vals?.under_pressure ?? 1))?.label || "?";
    return `Chute a ${dist}m, pressão ${press.toLowerCase()}`;
  };

  const mainLabel = labelMap[mainKey] || mainKey;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4 mt-4">
      {/* Question Header */}
      <div className="text-center">
        <p className="text-slate-300 text-sm font-medium">
          {simType === "shot" ? "Se esse chute fosse diferente, como muda a chance de gol?"
            : simType === "foul" ? "Se essa falta fosse diferente, como muda a chance de cartão?"
            : "Como as mudanças afetam o resultado da partida?"}
        </p>
      </div>

      {/* Comparison Cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* Real */}
        <div className="bg-slate-800/80 rounded-xl p-4 border border-blue-500/20 space-y-3">
          <span className="inline-block px-2 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-bold rounded-md uppercase tracking-wider">
            Cenário Real
          </span>
          <ProbCircle pct={basePct} label={mainLabel} color="#60A5FA" size={76} />
          {simType === "shot" && baseValues && (
            <div className="space-y-1 text-[11px] text-slate-500">
              <p>📏 Distância: <span className="text-slate-300">{baseValues.distance_to_goal}m</span></p>
              <p>🛡️ Pressão: <span className="text-slate-300">{PRESSURE_OPTIONS.find(p => p.value === baseValues.under_pressure)?.label}</span></p>
            </div>
          )}
        </div>
        {/* Simulated */}
        <div className="bg-slate-800/80 rounded-xl p-4 border border-brand-yellow/20 space-y-3">
          <span className="inline-block px-2 py-0.5 bg-brand-yellow/20 text-brand-yellow text-[10px] font-bold rounded-md uppercase tracking-wider">
            Cenário Simulado
          </span>
          <ProbCircle pct={simPct} label={mainLabel} color="#FFD700" size={76} />
          {simType === "shot" && overrideValues && (
            <div className="space-y-1 text-[11px] text-slate-500">
              <p>📏 Distância: <span className="text-slate-300">{overrideValues.distance_to_goal ?? baseValues?.distance_to_goal}m</span></p>
              <p>🛡️ Pressão: <span className="text-slate-300">{PRESSURE_OPTIONS.find(p => p.value === (overrideValues.under_pressure ?? baseValues?.under_pressure))?.label}</span></p>
            </div>
          )}
        </div>
      </div>

      {/* Multi-key deltas for match type */}
      {keys.length > 1 && (
        <div className="grid grid-cols-3 gap-2">
          {keys.map(k => {
            const d = Math.round((delta[k] || 0) * 100);
            const pos = d > 0;
            return (
              <div key={k} className={`rounded-xl p-3 border text-center ${pos ? "bg-green-500/10 border-green-500/20" : d < 0 ? "bg-red-500/10 border-red-500/20" : "bg-slate-800 border-slate-700"}`}>
                <p className="text-[10px] text-slate-500 uppercase">{labelMap[k] || k}</p>
                <p className={`text-lg font-bold ${pos ? "text-green-400" : d < 0 ? "text-red-400" : "text-slate-400"}`}>
                  {pos ? "+" : ""}{d}%
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Impact Card */}
      {keys.length <= 1 && (
        <div className={`rounded-xl p-4 border flex items-center gap-4 ${
          isZero ? "bg-slate-800 border-slate-700" : isPositive ? "bg-green-500/10 border-green-500/20" : "bg-red-500/10 border-red-500/20"
        }`}>
          <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
            isZero ? "bg-slate-700" : isPositive ? "bg-green-500/20" : "bg-red-500/20"
          }`}>
            {isZero ? <Minus size={20} className="text-slate-400" />
              : isPositive ? <TrendingUp size={20} className="text-green-400" />
              : <TrendingDown size={20} className="text-red-400" />}
          </div>
          <div>
            <p className="text-slate-400 text-xs">Impacto na {mainLabel}</p>
            <p className={`text-2xl font-extrabold ${isZero ? "text-slate-300" : isPositive ? "text-green-400" : "text-red-400"}`}>
              {isPositive ? "+" : ""}{deltaPct}%
            </p>
          </div>
        </div>
      )}

      {/* Narrative */}
      {narrative && (
        <div className="bg-gradient-to-br from-brand-yellow/5 to-yellow-500/5 rounded-xl p-4 border border-brand-yellow/10">
          <p className="text-brand-yellow text-xs font-bold mb-2 flex items-center gap-1.5">
            <Trophy size={14} /> Análise da Elli AI
          </p>
          <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{narrative}</p>
        </div>
      )}
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIMULADOR PRINCIPAL — SimulatorCard
   ═══════════════════════════════════════════════════════════════════════════ */

export default function SimulatorCard({ simType = "shot", isHome = 1, selectedMatch }) {
  // ─── State ─────────────────────────────────────────────────────────────
  const [values, setValues] = useState(() => {
    const base = simType === "shot" ? { ...BASE_SHOT } : simType === "foul" ? { ...BASE_FOUL } : { ...BASE_MATCH };
    base.is_home_team = isHome;

    // Sync with selected match if match type
    if (simType === "match" && selectedMatch) {
      const sc = (selectedMatch.score || "0-0").split("-").map(Number);
      base.home_score = sc[0] || 0;
      base.away_score = sc[1] || 0;
      base.minute = parseInt(selectedMatch.time) || 60;
    }
    return base;
  });

  const [overrides, setOverrides] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Pitch position (for shot type)
  const [pitchPos, setPitchPos] = useState({ x: 160, y: 130 });
  // Foul zone
  const [foulZone, setFoulZone] = useState("attack");
  // Foul pitch position
  const [foulPitchPos, setFoulPitchPos] = useState({ x: 160, y: 80 });

  // ─── Handlers ──────────────────────────────────────────────────────────
  const updateOverride = (key, val) => {
    setOverrides(prev => ({ ...prev, [key]: val }));
    setResult(null); // Reset result when changing
  };

  const handlePitchClick = (pos) => {
    setPitchPos(pos);
    setOverrides(prev => ({
      ...prev,
      distance_to_goal: pos.distance,
      angle_to_goal: pos.angle,
    }));
    setResult(null);
  };

  const handleFoulZoneChange = (zone) => {
    const z = FOUL_ZONES.find(fz => fz.id === zone);
    if (!z) return;
    setFoulZone(zone);
    setOverrides(prev => ({ ...prev, ...z.overrides }));
    // Update foul pitch position based on zone
    const yMap = { attack: 80, midfield: 170, defense: 260 };
    setFoulPitchPos({ x: 160, y: yMap[zone] || 170 });
    setResult(null);
  };

  const handleSimulate = async () => {
    const activeOverrides = { ...overrides };
    if (Object.keys(activeOverrides).length === 0) {
      setError("Altere pelo menos uma variável para simular!");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await simulateWhatIf({
        prediction_type: simType,
        base_data: values,
        overrides: activeOverrides,
        description: simType === "shot" ? "Simulação de chute" : simType === "foul" ? "Simulação de falta" : "Simulação de partida",
      });
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setOverrides({});
    setResult(null);
    setError(null);
  };

  // ─── Título ────────────────────────────────────────────────────────────
  const titles = {
    shot: { icon: "⚽", title: "Simulador de Chute", desc: "Ajuste as variáveis e veja como muda a P(gol)" },
    foul: { icon: "🟨", title: "Simulador de Falta", desc: "Ajuste o local e intensidade para ver P(cartão)" },
    match: { icon: "🏆", title: "Simulador de Partida", desc: "Altere estatísticas e veja o impacto no resultado" },
  };
  const t = titles[simType];

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <div className="w-full bg-slate-800/60 rounded-2xl border border-slate-700/80 overflow-hidden shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 bg-slate-800/90 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{t.icon}</span>
          <div>
            <h3 className="text-white font-bold text-sm">{t.title}</h3>
            <p className="text-slate-500 text-[11px]">{t.desc}</p>
          </div>
        </div>
        {Object.keys(overrides).length > 0 && (
          <button onClick={handleReset} className="text-slate-500 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-700" title="Resetar">
            <RotateCcw size={16} />
          </button>
        )}
      </div>

      {/* Controls */}
      <div className="p-5 space-y-5">
        {/* ── SHOT CONTROLS ────────────────────────────────────────── */}
        {simType === "shot" && (
          <>
            {/* Pitch + position */}
            <div>
              <p className="text-slate-500 text-[11px] mb-2 text-center">Clique no campo para posicionar o chute</p>
              <FootballPitch position={pitchPos} onPositionChange={handlePitchClick} variant="half" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <StyledSlider label="Distância do chute" icon="📏"
                value={overrides.distance_to_goal ?? values.distance_to_goal}
                min={3} max={40} unit="m"
                onChange={v => { updateOverride("distance_to_goal", v); setPitchPos(p => ({ ...p, y: 30 + (v / 40) * 170, distance: v })); }}
              />

              <SegmentedControl label="Pressão do adversário" icon="🛡️"
                options={PRESSURE_OPTIONS} value={overrides.under_pressure ?? values.under_pressure}
                onChange={v => updateOverride("under_pressure", v)}
              />

              <StyledSelect label="Tipo de finalização" icon="🦶"
                options={BODY_PARTS} value={overrides.body_part ?? values.body_part}
                onChange={v => updateOverride("body_part", v)}
              />

              <ToggleSwitch label="Gol aberto (sem goleiro)" icon="🥅"
                value={overrides.open_goal ?? values.open_goal}
                onChange={v => updateOverride("open_goal", v)}
              />

              <ToggleSwitch label="Chute de primeira" icon="⚡"
                value={overrides.first_time ?? values.first_time}
                onChange={v => updateOverride("first_time", v)}
              />
            </div>
          </>
        )}

        {/* ── FOUL CONTROLS ────────────────────────────────────────── */}
        {simType === "foul" && (
          <>
            {/* Zone Selection */}
            <div className="space-y-2">
              <span className="text-slate-400 text-xs font-medium flex items-center gap-1.5">
                <span className="text-sm">📍</span> Zona da falta
              </span>
              <div className="grid grid-cols-3 gap-2">
                {FOUL_ZONES.map(z => (
                  <button key={z.id} onClick={() => handleFoulZoneChange(z.id)}
                    className={`p-3 rounded-xl border text-center transition-all ${
                      foulZone === z.id
                        ? "bg-brand-yellow/15 border-brand-yellow/40 text-white"
                        : "bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-600"
                    }`}>
                    <span className="text-xl">{z.icon}</span>
                    <p className="text-xs font-bold mt-1">{z.label}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{z.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Pitch with zones */}
            <FootballPitch position={foulPitchPos} onPositionChange={(pos) => { setFoulPitchPos(pos); setResult(null); }}
              variant="full" highlightZone={foulZone} />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <StyledSlider label="Minuto da partida" icon="⏱️"
                value={overrides.minute ?? values.minute}
                min={1} max={120} unit="'"
                onChange={v => updateOverride("minute", v)}
              />
              <SegmentedControl label="Pressão no lance" icon="🛡️"
                options={PRESSURE_OPTIONS} value={overrides.under_pressure ?? values.under_pressure}
                onChange={v => updateOverride("under_pressure", v)}
              />
              <ToggleSwitch label="Time está perdendo?" icon="📉"
                value={overrides.team_losing ?? values.team_losing}
                onChange={v => updateOverride("team_losing", v)}
              />
              <ToggleSwitch label="Time da casa?" icon="🏠"
                value={overrides.is_home_team ?? values.is_home_team}
                onChange={v => updateOverride("is_home_team", v)}
              />
            </div>
          </>
        )}

        {/* ── MATCH CONTROLS ───────────────────────────────────────── */}
        {simType === "match" && (
          <>
            {/* Scoreboard */}
            <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-700">
              <div className="flex items-center justify-between">
                <div className="text-center flex-1">
                  <p className="text-slate-400 text-[11px] uppercase tracking-wider mb-1">Casa</p>
                  <p className="text-white font-bold text-sm truncate">{selectedMatch?.home_team || "Mandante"}</p>
                </div>
                <div className="flex items-center gap-3 px-4">
                  <Stepper label="" value={overrides.home_score ?? values.home_score}
                    onChange={v => updateOverride("home_score", v)} min={0} max={10} />
                  <span className="text-slate-600 text-xl font-light">×</span>
                  <Stepper label="" value={overrides.away_score ?? values.away_score}
                    onChange={v => updateOverride("away_score", v)} min={0} max={10} />
                </div>
                <div className="text-center flex-1">
                  <p className="text-slate-400 text-[11px] uppercase tracking-wider mb-1">Fora</p>
                  <p className="text-white font-bold text-sm truncate">{selectedMatch?.away_team || "Visitante"}</p>
                </div>
              </div>
            </div>

            {/* Stats Sliders */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <StyledSlider label="Minuto" icon="⏱️"
                value={overrides.minute ?? values.minute} min={1} max={120} unit="'"
                onChange={v => updateOverride("minute", v)} />
              <StyledSlider label="Domínio Territorial" icon="🗺️"
                value={overrides.pressure_ratio ?? values.pressure_ratio} min={0.3} max={3} step={0.1} unit="x"
                onChange={v => updateOverride("pressure_ratio", v)} />
              <StyledSlider label="Oportunidades (Casa)" icon="🎯"
                value={overrides.home_xg ?? values.home_xg} min={0} max={5} step={0.1}
                onChange={v => updateOverride("home_xg", v)} />
              <StyledSlider label="Oportunidades (Fora)" icon="🎯"
                value={overrides.away_xg ?? values.away_xg} min={0} max={5} step={0.1}
                onChange={v => updateOverride("away_xg", v)} />
              <Stepper label="Finalizações (Casa)" icon="⚽"
                value={overrides.home_shots ?? values.home_shots}
                onChange={v => updateOverride("home_shots", v)} min={0} max={30} />
              <Stepper label="Finalizações (Fora)" icon="⚽"
                value={overrides.away_shots ?? values.away_shots}
                onChange={v => updateOverride("away_shots", v)} min={0} max={30} />
              <StyledSlider label="Efetividade Posse (Casa)" icon="📊"
                value={overrides.home_pass_acc ?? values.home_pass_acc} min={0.4} max={1} step={0.01}
                onChange={v => updateOverride("home_pass_acc", v)} />
              <StyledSlider label="Efetividade Posse (Fora)" icon="📊"
                value={overrides.away_pass_acc ?? values.away_pass_acc} min={0.4} max={1} step={0.01}
                onChange={v => updateOverride("away_pass_acc", v)} />
            </div>
          </>
        )}

        {/* ── SIMULATE BUTTON ──────────────────────────────────────── */}
        <button onClick={handleSimulate} disabled={loading}
          className="w-full py-3.5 bg-brand-yellow hover:bg-yellow-400 text-slate-900 font-extrabold rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-brand-yellow/20 text-sm active:scale-[0.98]"
        >
          {loading ? (
            <><motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}><Play size={16} /></motion.div> Simulando...</>
          ) : (
            <><Play size={16} /> Rodar Simulação</>
          )}
        </button>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
              className="bg-red-900/20 border border-red-700/30 rounded-xl p-3 text-red-300 text-xs">
              ⚠️ {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Result */}
        {result && (
          <SimulatorResult
            simType={simType}
            base={result.base}
            simulated={result.simulated}
            delta={result.delta}
            narrative={result.narrative}
            baseValues={values}
            overrideValues={overrides}
          />
        )}
      </div>
    </div>
  );
}
