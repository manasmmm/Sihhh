import React, { useEffect, useState } from 'react';
import { X, Activity, Loader2 } from 'lucide-react';
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
import { fetchBasinAverage } from '../api';
import { BasinAverageData } from '../types';

interface BasinAverageModalProps {
  currentDepth: number;
  currentDate: string;
  onClose: () => void;
}

export const BasinAverageModal: React.FC<BasinAverageModalProps> = ({
  currentDepth,
  currentDate,
  onClose,
}) => {
  const [data, setData] = useState<BasinAverageData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetchBasinAverage(currentDepth)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load basin average:', err);
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [currentDepth]);

  const chartData = data
    ? data.dates.map((d, i) => ({
        date: d,
        temperature: data.temperature_c[i],
      }))
    : [];

  return (
    <div
      className="copernicus-panel p-3.5 text-slate-200 pointer-events-auto flex flex-col gap-2.5"
      style={{
        width: '380px',
        backgroundColor: 'rgba(15, 23, 36, 0.95)',
        border: '1px solid rgba(79, 209, 197, 0.3)',
        borderRadius: '12px',
        boxShadow: '0 16px 40px rgba(0,0,0,0.7)',
      }}
    >
      <div className="flex items-center justify-between border-b border-white/10 pb-2">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-[#4fd1c5]/20 text-[#4fd1c5]">
            <Activity size={15} />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-white">
              Basin-Average Temperature
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              Spatial mean over North Indian Ocean (depth: {currentDepth}m)
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X size={15} />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-10 gap-2 text-xs text-[#4fd1c5]">
          <Loader2 size={16} className="animate-spin" />
          <span>Computing spatial basin mean...</span>
        </div>
      ) : data ? (
        <>
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
                  interval={25}
                  tickFormatter={(val: string) => {
                    const p = val.split('-');
                    const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May'][parseInt(p[1], 10) - 1];
                    return `${m} ${p[2]}`;
                  }}
                />
                <YAxis
                  dataKey="temperature"
                  stroke="#64748b"
                  tick={{ fill: '#94a3b8', fontSize: 9 }}
                  unit="°C"
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const row = payload[0].payload;
                      return (
                        <div className="p-2 rounded bg-slate-900/95 border border-[#4fd1c5]/40 text-[11px] font-mono text-white">
                          <div>Date: {row.date}</div>
                          <div className="text-[#4fd1c5] font-bold">
                            Basin Mean: {row.temperature} °C
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <ReferenceLine
                  x={currentDate}
                  stroke="#fb923c"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                />
                <Line
                  type="monotone"
                  dataKey="temperature"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center justify-between text-[10px] font-mono px-2 py-1 rounded bg-white/5 text-slate-300 border border-white/5">
            <span>Basin Min: <b className="text-blue-400">{data.stats.min}°C</b></span>
            <span>Median: <b className="text-[#4fd1c5]">{data.stats.median}°C</b></span>
            <span>Max: <b className="text-orange-400">{data.stats.max}°C</b></span>
          </div>
        </>
      ) : null}
    </div>
  );
};
