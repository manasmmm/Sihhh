import React, { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';

interface ProfileMiniChartProps {
  depths: number[];
  temps: (number | null)[];
  d20: number | null;
  mld: number | null;
  maxDepth: number;
  height?: number;
}

/** Small vertical temperature profile (depth downwards) with D20 and MLD marked. */
export const ProfileMiniChart: React.FC<ProfileMiniChartProps> = ({ depths, temps, d20, mld, maxDepth, height = 150 }) => {
  const data = useMemo(
    () => depths.map((d, i) => ({ depth: d, temperature: temps[i] })).filter((p) => p.depth <= maxDepth),
    [depths, temps, maxDepth]
  );
  const vals = data.map((d) => d.temperature).filter((v): v is number => v !== null);
  const tMin = vals.length ? Math.floor(Math.min(...vals) - 1) : 0;
  const tMax = vals.length ? Math.ceil(Math.max(...vals) + 1) : 32;
  const ticks = maxDepth <= 300 ? [0, 50, 100, 150, 200, 300] : [0, 200, 400, 600, 800, 1000];

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart layout="vertical" data={data} margin={{ top: 6, right: 10, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="temperature" type="number" domain={[tMin, tMax]} stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 9 }} unit="°" />
          <YAxis
            dataKey="depth"
            type="number"
            reversed
            domain={[0, maxDepth]}
            ticks={ticks}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 9 }}
            unit="m"
            allowDataOverflow
          />
          <Tooltip
            content={({ active, payload }) =>
              active && payload && payload.length ? (
                <div className="p-1.5 rounded bg-slate-900/95 border border-[#38bdf8]/40 text-[10px] font-mono text-white">
                  {payload[0].payload.depth} m: {payload[0].payload.temperature ?? '—'} °C
                </div>
              ) : null
            }
          />
          {d20 !== null && d20 <= maxDepth && (
            <ReferenceLine
              y={d20}
              stroke="#f472b6"
              strokeDasharray="3 3"
              label={{ value: `D20 ${Math.round(d20)}m`, fill: '#f472b6', fontSize: 9, position: 'insideBottomRight' }}
            />
          )}
          {mld !== null && mld <= maxDepth && (
            <ReferenceLine
              y={mld}
              stroke="#facc15"
              strokeDasharray="3 3"
              label={{ value: `MLD ${Math.round(mld)}m`, fill: '#facc15', fontSize: 9, position: 'insideTopRight' }}
            />
          )}
          <Line
            type="monotone"
            dataKey="temperature"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={{ r: 2, fill: '#38bdf8', stroke: '#0f172a', strokeWidth: 1 }}
            isAnimationActive={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
