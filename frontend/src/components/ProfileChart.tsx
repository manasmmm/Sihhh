import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { ProfileResponse } from '../types';

interface ProfileChartProps {
  profile: ProfileResponse;
  currentDepth: number;
}

export const ProfileChart: React.FC<ProfileChartProps> = ({
  profile,
  currentDepth,
}) => {
  const chartData = useMemo(() => {
    return profile.depths_m.map((d, i) => ({
      depth: d,
      temperature: profile.temperature_c[i],
    }));
  }, [profile]);

  // Current temperature at active depth
  const currentTemp = useMemo(() => {
    const idx = profile.depths_m.indexOf(currentDepth);
    if (idx >= 0 && profile.temperature_c[idx] !== null) {
      return profile.temperature_c[idx];
    }
    return null;
  }, [profile, currentDepth]);

  return (
    <div className="flex flex-col gap-1 w-full select-none">
      <div className="flex items-center justify-between text-[11px] text-slate-300 font-medium">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#38bdf8]"></span>
          Vertical Temperature Profile
        </span>
        <span className="text-slate-400 font-mono text-[10px]">
          {profile.date}
        </span>
      </div>

      <div style={{ width: '100%', height: 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            layout="vertical"
            data={chartData}
            margin={{ top: 8, right: 12, left: -16, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            {/* Temperature on X-Axis */}
            <XAxis
              dataKey="temperature"
              type="number"
              domain={[0, 32]}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 9 }}
              unit="°C"
            />
            {/* Depth on Y-Axis, reversed so 0m is at top */}
            <YAxis
              dataKey="depth"
              type="number"
              reversed={true}
              domain={[0, 1000]}
              ticks={[0, 100, 250, 500, 750, 1000]}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 9 }}
              unit="m"
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="p-2 rounded bg-slate-900/95 border border-[#38bdf8]/40 shadow-lg text-[11px] font-mono text-white">
                      <div>Depth: {data.depth} m</div>
                      <div className="text-[#38bdf8] font-bold">
                        Temp: {data.temperature ?? 'N/A'} °C
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            {/* Horizontal line at currently selected depth */}
            <ReferenceLine
              y={currentDepth}
              stroke="#4fd1c5"
              strokeWidth={2}
              strokeDasharray="4 2"
              label={{
                value: `${currentDepth}m`,
                fill: '#4fd1c5',
                fontSize: 9,
                position: 'right',
              }}
            />
            {/* Derived markers: warm-layer depth (D20) and mixed-layer depth */}
            {profile.derived?.d20 != null && (
              <ReferenceLine
                y={profile.derived.d20}
                stroke="#f472b6"
                strokeWidth={1.4}
                strokeDasharray="2 3"
                label={{ value: `D20 ${Math.round(profile.derived.d20)}m`, fill: '#f472b6', fontSize: 9, position: 'insideTopLeft' }}
              />
            )}
            {profile.derived?.mld != null && (
              <ReferenceLine
                y={profile.derived.mld}
                stroke="#facc15"
                strokeWidth={1.4}
                strokeDasharray="2 3"
                label={{ value: `MLD ${Math.round(profile.derived.mld)}m`, fill: '#facc15', fontSize: 9, position: 'insideBottomLeft' }}
              />
            )}
            <Line
              type="monotone"
              dataKey="temperature"
              stroke="#38bdf8"
              strokeWidth={2.2}
              dot={{ r: 2.5, fill: '#38bdf8', stroke: '#0f172a', strokeWidth: 1 }}
              activeDot={{ r: 5, fill: '#ffffff', stroke: '#38bdf8', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Min / Current / Max annotation row */}
      <div className="flex items-center justify-between text-[10px] font-mono px-1 py-1 rounded bg-white/5 text-slate-300 border border-white/5">
        <span>Min: <b className="text-blue-400">{profile.stats.min ?? '--'}°C</b></span>
        <span>
          At {currentDepth}m: <b className="text-[#4fd1c5]">{currentTemp ?? '--'}°C</b>
        </span>
        <span>Max: <b className="text-orange-400">{profile.stats.max ?? '--'}°C</b></span>
      </div>
    </div>
  );
};
