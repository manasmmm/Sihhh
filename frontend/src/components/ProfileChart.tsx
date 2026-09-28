import React, { useMemo } from 'react';
import { displayDate } from '../i18n';
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

// Depth is plotted on a square-root scale: the upper ocean (mixed layer, thermocline),
// where most of the structure is, gets more room while the axis still reaches 1000 m.
const toAxis = (depth: number) => Math.sqrt(Math.max(depth, 0));
const DEPTH_TICKS = [0, 25, 50, 100, 200, 300, 500, 1000];

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
      depthAxis: toAxis(d),
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
          {displayDate(profile.date)}
        </span>
      </div>

      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            layout="vertical"
            data={chartData}
            margin={{ top: 8, right: 14, left: -12, bottom: 4 }}
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
            {/* Depth on Y-Axis (0 m at top), square-root scale */}
            <YAxis
              dataKey="depthAxis"
              type="number"
              reversed={true}
              domain={[0, toAxis(1000)]}
              ticks={DEPTH_TICKS.map(toAxis)}
              tickFormatter={(v: number) => `${Math.round(v * v)}m`}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 9 }}
              width={48}
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
            {/* Selected depth, warm-layer depth (D20) and mixed-layer depth; values are in the key below */}
            {profile.derived?.mld != null && (
              <ReferenceLine y={toAxis(profile.derived.mld)} stroke="#facc15" strokeWidth={1.8} strokeDasharray="5 3" />
            )}
            {profile.derived?.d20 != null && (
              <ReferenceLine y={toAxis(profile.derived.d20)} stroke="#f472b6" strokeWidth={1.8} strokeDasharray="5 3" />
            )}
            <ReferenceLine y={toAxis(currentDepth)} stroke="#4fd1c5" strokeWidth={1.5} strokeOpacity={0.8} />
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

      {/* Key for the reference lines */}
      <div className="flex items-center justify-between gap-2 text-[10px] font-mono px-1 text-slate-300">
        <span className="flex items-center gap-1.5" title="Mixed-layer depth: upper water stirred by the wind">
          <span className="inline-block w-4 border-t-2 border-dashed border-[#facc15]" />
          MLD <b className="text-[#facc15]">{profile.derived?.mld != null ? `${Math.round(profile.derived.mld)} m` : 'n/a'}</b>
        </span>
        <span className="flex items-center gap-1.5" title="Warm-layer depth: where the water cools to 20 °C (thermocline marker)">
          <span className="inline-block w-4 border-t-2 border-dashed border-[#f472b6]" />
          D20 <b className="text-[#f472b6]">{profile.derived?.d20 != null ? `${Math.round(profile.derived.d20)} m` : 'n/a'}</b>
        </span>
        <span className="flex items-center gap-1.5" title="Depth selected on the depth rail">
          <span className="inline-block w-4 border-t-2 border-[#4fd1c5]" />
          Selected <b className="text-[#4fd1c5]">{currentDepth} m</b>
        </span>
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
