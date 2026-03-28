import React from 'react';

export default function CustomFloatingTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="relative bg-slate-800 border border-slate-600 p-4 rounded-xl shadow-2xl text-center min-w-[140px] z-50">
        <p className="text-slate-400 text-[10px] font-extrabold uppercase tracking-widest mb-2 border-b border-slate-700 pb-2">{label}</p>
        
        {payload.map((entry, index) => (
          <p key={index} className="text-[13px] font-bold flex items-center justify-between space-x-3 w-full my-1">
            <span className="text-slate-300">{entry.name}:</span>
            <span style={{ color: entry.color }}>{entry.value}</span>
          </p>
        ))}

        {/* CSS Downward Triangle/Arrow pointing from the tooltip */}
        <div className="absolute -bottom-2.5 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-[10px] border-r-[10px] border-t-[10px] border-transparent border-t-slate-800 drop-shadow-md"></div>
      </div>
    );
  }
  return null;
}
