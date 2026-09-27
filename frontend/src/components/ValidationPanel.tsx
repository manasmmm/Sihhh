import React, { useEffect, useState } from 'react';
import { ShieldCheck, X, Loader2 } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';
import { ValidationData } from '../types';
import { fetchValidation } from '../api';

interface ValidationPanelProps {
  onClose: () => void;
}

/** Per-depth validation metrics from data/validation/validation_metrics.json. Never shows invented numbers. */
export const ValidationPanel: React.FC<ValidationPanelProps> = ({ onClose }) => {
  const [data, setData] = useState<ValidationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchValidation()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const isFinal = data?.status === 'final';
  const fmt = (v: number | null, nd = 2) => (v === null || v === undefined ? '—' : v.toFixed(nd));

  return (
    <div
      className="copernicus-panel p-4 text-xs flex flex-col gap-3 pointer-events-auto animate-fade-in"
      style={{ width: '320px', backgroundColor: 'rgba(12, 20, 35, 0.94)', maxHeight: 'calc(100vh - 330px)', overflowY: 'auto' }}
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-semibold text-white text-[12px]">
          <ShieldCheck size={14} className="text-[#4fd1c5]" />
          Model validation
        </span>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10"
          title="Close validation panel"
        >
          <X size={14} />
        </button>
      </div>

      {!data && !error && (
        <div className="flex items-center gap-2 text-[#4fd1c5]">
          <Loader2 size={14} className="animate-spin" /> Loading…
        </div>
      )}
      {error && <div className="text-rose-300">Could not load validation metrics: {error}</div>}

      {data && (
        <>
          <div className="flex flex-col gap-1 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-500">Reference</span>
              <span className="text-slate-200">{data.reference ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Period</span>
              <span className="text-slate-200">{data.period ?? '—'}</span>
            </div>
          </div>

          {!isFinal ? (
            <div className="px-3 py-3 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[11px] font-medium text-center">
              {data.message ?? 'Validation results pending'}
            </div>
          ) : (
            <>
              <div style={{ width: '100%', height: 170 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    layout="vertical"
                    data={data.metrics.map((m) => ({ depth: `${m.depth_m}`, rmse: m.rmse_c, bias: m.bias_c }))}
                    margin={{ top: 4, right: 8, left: -18, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis type="number" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 9 }} unit="°C" />
                    <YAxis type="category" dataKey="depth" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 9 }} unit="m" width={52} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid rgba(79,209,197,0.3)', fontSize: 11 }}
                      labelFormatter={(l) => `${l} m`}
                    />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <ReferenceLine x={0} stroke="#64748b" />
                    <Bar dataKey="rmse" name="RMSE" fill="#38bdf8" isAnimationActive={false} />
                    <Bar dataKey="bias" name="Bias" fill="#f59e0b" isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <table className="w-full text-[10.5px] font-mono">
                <thead>
                  <tr className="text-slate-500">
                    <th className="text-left font-medium py-1">Depth</th>
                    <th className="text-right font-medium">RMSE °C</th>
                    <th className="text-right font-medium">Bias °C</th>
                    <th className="text-right font-medium">Corr</th>
                    <th className="text-right font-medium">n</th>
                  </tr>
                </thead>
                <tbody>
                  {data.metrics.map((m) => (
                    <tr key={m.depth_m} className="border-t border-white/5 text-slate-300">
                      <td className="py-0.5">{m.depth_m} m</td>
                      <td className="text-right">{fmt(m.rmse_c)}</td>
                      <td className="text-right">{fmt(m.bias_c)}</td>
                      <td className="text-right">{fmt(m.corr)}</td>
                      <td className="text-right">{m.n ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </div>
  );
};
