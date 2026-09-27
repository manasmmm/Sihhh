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

const fmt = (v: number | null | undefined, nd = 2) => (v === null || v === undefined ? '—' : v.toFixed(nd));

/**
 * Per-depth validation metrics from data/validation/validation_metrics.json,
 * shown as a centred window so nothing on the map (time slider, cards) covers it.
 * Never shows invented numbers: a placeholder file shows "Validation results pending".
 */
export const ValidationPanel: React.FC<ValidationPanelProps> = ({ onClose }) => {
  const [data, setData] = useState<ValidationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchValidation()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const isFinal = data?.status === 'final';
  const chartData = (data?.metrics ?? []).map((m) => ({ depth: `${m.depth_m} m`, rmse: m.rmse_c, bias: m.bias_c }));

  return (
    <div
      className="fixed inset-0 z-[3000] flex items-center justify-center bg-black/55 backdrop-blur-[2px] animate-fade-in p-4"
      onClick={onClose}
    >
      <div
        className="copernicus-panel p-5 flex flex-col gap-4 text-slate-200"
        style={{ width: 'min(860px, 96vw)', maxHeight: '90vh', overflowY: 'auto', backgroundColor: 'rgba(12, 20, 35, 0.98)' }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Model validation"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-shrink-0">
          <div>
            <div className="flex items-center gap-2 font-semibold text-white text-[15px]">
              <ShieldCheck size={17} className="text-[#4fd1c5]" />
              Model validation
            </div>
            {data && (
              <div className="mt-1.5 grid grid-cols-[80px_1fr] gap-x-2 gap-y-0.5 text-[11.5px]">
                <span className="text-slate-500">Reference</span>
                <span className="text-slate-200">{data.reference ?? '—'}</span>
                <span className="text-slate-500">Period</span>
                <span className="text-slate-200">{data.period ?? '—'}</span>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 flex-shrink-0"
            title="Close (Esc)"
          >
            <X size={17} />
          </button>
        </div>

        {!data && !error && (
          <div className="flex items-center gap-2 text-[#4fd1c5] text-sm">
            <Loader2 size={16} className="animate-spin" /> Loading…
          </div>
        )}
        {error && <div className="text-rose-300 text-sm">Could not load validation metrics: {error}</div>}

        {data && !isFinal && (
          <div className="px-4 py-4 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 text-sm font-medium text-center">
            {data.message ?? 'Validation results pending'}
          </div>
        )}

        {data && isFinal && (
          <div className="flex flex-wrap gap-5 flex-shrink-0">
            {/* Chart: depth downwards, RMSE and bias per depth */}
            <div className="flex-1 min-w-[300px] flex flex-col gap-1">
              <div className="text-[11.5px] text-slate-400">Error by depth (°C)</div>
              <div style={{ width: '100%', height: 400 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart layout="vertical" data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 4 }} barGap={1}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" horizontal={false} />
                    <XAxis type="number" stroke="#64748b" tick={{ fill: '#cbd5e1', fontSize: 11 }} unit="°C" />
                    <YAxis type="category" dataKey="depth" stroke="#64748b" tick={{ fill: '#cbd5e1', fontSize: 11 }} width={56} interval={0} />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                      contentStyle={{ background: '#0f172a', border: '1px solid rgba(79,209,197,0.35)', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: '#e2e8f0' }}
                      formatter={(v: number, name: string) => [`${v?.toFixed(2)} °C`, name]}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <ReferenceLine x={0} stroke="#94a3b8" />
                    <Bar dataKey="rmse" name="RMSE" fill="#38bdf8" isAnimationActive={false} barSize={9} />
                    <Bar dataKey="bias" name="Bias" fill="#f59e0b" isAnimationActive={false} barSize={9} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Table */}
            <div className="flex-1 min-w-[300px]">
              <table className="w-full text-[12px] font-mono">
                <thead>
                  <tr className="text-slate-400 border-b border-white/10">
                    <th className="text-left font-medium py-1.5">Depth</th>
                    <th className="text-right font-medium">RMSE °C</th>
                    <th className="text-right font-medium">Bias °C</th>
                    <th className="text-right font-medium">Corr</th>
                    <th className="text-right font-medium">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {data.metrics.map((m) => (
                    <tr key={m.depth_m} className="border-b border-white/5 text-slate-200">
                      <td className="py-[5px]">{m.depth_m} m</td>
                      <td className="text-right text-[#7dd3fc]">{fmt(m.rmse_c)}</td>
                      <td className="text-right text-[#fbbf24]">{fmt(m.bias_c)}</td>
                      <td className="text-right">{fmt(m.corr)}</td>
                      <td className="text-right text-slate-400">{m.n?.toLocaleString('en-IN') ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-2 text-[10.5px] text-slate-500 leading-snug">
                RMSE: typical size of the error. Bias: average over- (+) or under- (−) estimate. Corr: pattern
                agreement with the reference (1 = perfect).
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
