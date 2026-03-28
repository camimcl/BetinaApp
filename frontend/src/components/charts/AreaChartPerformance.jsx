import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import CustomFloatingTooltip from './CustomFloatingTooltip';

const data = [
  { name: 'Jan', performance: 2000 },
  { name: 'Fev', performance: 3500 },
  { name: 'Mar', performance: 2800 },
  { name: 'Abr', performance: 5000 },
  { name: 'Mai', performance: 4800 },
  { name: 'Jun', performance: 7500 },
];

export default function AreaChartPerformance() {
  return (
    <div className="w-full h-[280px] mt-6">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
        <AreaChart
          data={data}
          margin={{ top: 20, right: 10, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorBrandYellow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FFD700" stopOpacity={0.5}/>
              <stop offset="95%" stopColor="#FFD700" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis 
            dataKey="name" 
            stroke="#94a3b8" 
            fontSize={11} 
            tickLine={false} 
            axisLine={false}
            dy={10}
          />
          <YAxis 
            stroke="#94a3b8" 
            fontSize={11} 
            tickLine={false} 
            axisLine={false}
            tickFormatter={(value) => `R$${value/1000}k`}
          />
          <Tooltip content={<CustomFloatingTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1, strokeDasharray: '4 4' }} />
          <Area 
            type="monotone" 
            dataKey="performance" 
            stroke="#FFD700" 
            strokeWidth={4}
            fillOpacity={1} 
            fill="url(#colorBrandYellow)" 
            name="Rendimento"
            activeDot={{ r: 8, fill: '#FFD700', stroke: '#1e293b', strokeWidth: 3 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
