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
import { TimeseriesResponse } from '../types';

interface TimeseriesChartProps {
  timeseries: TimeseriesResponse;
  currentDate: string;
}

export const TimeseriesChart: React.FC<TimeseriesChartProps> = ({
  timeseries,
  currentDate,
}) => {
  const chartData = useMemo(() => {
    return timeseries.dates.map((d, i) => {
      // Short label: "Jan 15"
      const parts = d.split('-');
      const monthNames = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
      ];
      const mIdx = parseInt(parts[1], 10) - 1;
      const shortLabel = `${monthNames[mIdx]} ${parts[2]}`;

      return {
        date: d,
        shortDate: shortLabel,
        temperature: timeseries.temperature_c[i],
      };
    });
  }, [timeseries]);

  // Compute domain bounds
  const yDomain = useMemo(() => {
    const min = timeseries.stats.min ?? 20;
    const max = timeseries.stats.max ?? 30;
    return [Math.floor(min - 1), Math.ceil(max + 1)];
  }, [timeseries.stats]);

  return (
    <div className="flex flex-col gap-1 w-full select-none">
      <div className="flex items-center justify-between text-[11px] text-slate-300 font-medium">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#4fd1c5]"></span>
          Temperature Over Time
        </span>
        <span className="text-slate-400 font-mono text-[10px]">
          Depth: {timeseries.depth} m
        </span>
      </div>

      <div style={{ width: '100%', height: 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 8, right: 12, left: -16, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="date"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 9 }}
              interval={24}
              tickFormatter={(val: string) => {
                const p = val.split('-');
                const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May'][parseInt(p[1], 10) - 1];
                return `${m} ${p[2]}`;
              }}
            />
            <YAxis
              dataKey="temperature"
              domain={yDomain}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 9 }}
              unit="°C"
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="p-2 rounded bg-slate-900/95 border border-[#4fd1c5]/40 shadow-lg text-[11px] font-mono text-white">
                      <div>Date: {data.date}</div>
                      <div className="text-[#4fd1c5] font-bold">
                        Temp: {data.temperature ?? 'N/A'} °C
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            {/* Vertical reference line at currently active date */}
            <ReferenceLine
              x={currentDate}
              stroke="#fb923c"
              strokeWidth={2}
              strokeDasharray="4 2"
              label={{
                value: 'Selected',
                fill: '#fb923c',
                fontSize: 9,
                position: 'top',
              }}
            />
            <Line
              type="monotone"
              dataKey="temperature"
              stroke="#4fd1c5"
              strokeWidth={2.2}
              dot={false}
              activeDot={{ r: 4, fill: '#ffffff', stroke: '#4fd1c5', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Min / Median / Max annotation row */}
      <div className="flex items-center justify-between text-[10px] font-mono px-1 py-1 rounded bg-white/5 text-slate-300 border border-white/5">
        <span>Min: <b className="text-blue-400">{timeseries.stats.min ?? '--'}°C</b></span>
        <span>Median: <b className="text-[#4fd1c5]">{timeseries.stats.median ?? '--'}°C</b></span>
        <span>Max: <b className="text-orange-400">{timeseries.stats.max ?? '--'}°C</b></span>
      </div>
    </div>
  );
};
