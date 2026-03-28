import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import CustomFloatingTooltip from './CustomFloatingTooltip';

const data = [
  { name: 'Seg', lucros: 400, perdas: 240 },
  { name: 'Ter', lucros: 300, perdas: 139 },
  { name: 'Qua', lucros: 200, perdas: 580 },
  { name: 'Qui', lucros: 278, perdas: 390 },
  { name: 'Sex', lucros: 189, perdas: 480 },
  { name: 'Sáb', lucros: 639, perdas: 380 },
  { name: 'Dom', lucros: 549, perdas: 430 },
];

export default function BarChartAnalytics() {
  return (
    <div className="w-full h-[280px] mt-6">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 10, left: -20, bottom: 0 }}
          barSize={14}
        >
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
          />
          <Tooltip content={<CustomFloatingTooltip />} cursor={{fill: '#1e293b', opacity: 0.4}} />
          {/* Blue bars for generic stats / losses */}
          <Bar dataKey="perdas" name="Perdas" fill="#3b82f6" radius={[6, 6, 0, 0]} />
          {/* Yellow bars for primary brand / profits */}
          <Bar dataKey="lucros" name="Lucros" fill="#FFD700" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
