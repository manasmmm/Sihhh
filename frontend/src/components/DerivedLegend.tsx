import React, { useEffect, useState } from 'react';
import { Layers } from 'lucide-react';
import { DerivedLegendInfo, DerivedVar } from '../types';
import { fetchDerivedLegend } from '../api';

interface DerivedLegendProps {
  variable: DerivedVar;
  title: string;
  /** Extra line under the bar, e.g. "Confidence not available" */
  note?: string | null;
  width?: number;
  labels?: { thresholdTemplate?: string; ssfYes?: string; ssfNo?: string; confidenceNote?: string };
}

const UNIT_LABEL: Record<string, string> = { 'degC km-1': '°C/km', 'kJ cm-2': 'kJ/cm²', '1': '' };

function fmt(v: number, units: string): string {
  if (units === 'degC km-1') return v.toFixed(3);
  if (Math.abs(v) < 10 && !Number.isInteger(v)) return v.toFixed(1);
  return String(Math.round(v));
}

/** Legend for derived layers; colours come from the backend so they match the PNG exactly. */
export const DerivedLegend: React.FC<DerivedLegendProps> = ({ variable, title, note, width = 280, labels }) => {
  const [info, setInfo] = useState<DerivedLegendInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDerivedLegend(variable)
      .then((i) => !cancelled && setInfo(i))
      .catch((e) => console.error('Legend load failed', e));
    return () => {
      cancelled = true;
    };
  }, [variable]);

  const unit = info ? UNIT_LABEL[info.units] ?? info.units : '';
  const isFront = variable.startsWith('front');
  const thresholdText = info
    ? (labels?.thresholdTemplate ?? 'Front threshold {value} °C/km (starting value, to be tuned)').replace(
        '{value}',
        String(info.front_threshold_c_per_km)
      )
    : '';

  return (
    <div
      className="copernicus-panel px-3.5 py-2.5 text-xs flex flex-col gap-2 pointer-events-auto select-none"
      style={{ width, backgroundColor: 'rgba(12, 20, 35, 0.92)' }}
    >
      <div className="flex items-center gap-2 text-[11px] font-medium">
        <Layers size={13} className="text-[#4fd1c5]" />
        <span className="text-white font-semibold">{title}</span>
        {unit && <span className="text-[10px] text-slate-500 font-mono px-1.5 py-0.5 rounded bg-white/[0.04]">{unit}</span>}
      </div>

      {info && variable === 'subsurface_front_flag' ? (
        <div className="flex flex-col gap-1 text-[10px] text-slate-300">
          <span className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm" style={{ background: info.stops[1] }} />
            {labels?.ssfYes ?? 'Front at 50 m, not at surface'}
          </span>
          <span className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm border border-white/20" />
            {labels?.ssfNo ?? 'No subsurface-only front'}
          </span>
        </div>
      ) : info ? (
        <>
          <div className="relative">
            <div
              style={{
                background: `linear-gradient(to right, ${info.stops.join(', ')})`,
                height: '12px',
                borderRadius: '5px',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            />
            {isFront && info.vmax > 0 && (
              <div
                className="absolute -top-1 -bottom-1 w-[2px] bg-white"
                style={{ left: `${Math.min(100, (info.front_threshold_c_per_km / info.vmax) * 100)}%` }}
                title="Front threshold"
              />
            )}
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 font-mono">
            {[0, 0.25, 0.5, 0.75, 1].map((f) => (
              <span key={f}>
                {fmt(info.vmin + f * (info.vmax - info.vmin), info.units)}
                {f === 1 && (variable === 'd20' || variable === 'mld' || variable === 'd26') ? '+' : ''}
              </span>
            ))}
          </div>
        </>
      ) : (
        <div className="h-5" />
      )}

      {(isFront || variable === 'subsurface_front_flag') && info && (
        <div className="text-[9.5px] text-slate-400 leading-snug">{thresholdText}</div>
      )}
      {variable === 'confidence' && (
        <div className="text-[9.5px] text-slate-400 leading-snug">
          {labels?.confidenceNote ?? 'Indicative data-density index, not a statistical error estimate'}
        </div>
      )}
      {note && <div className="text-[10px] text-amber-300/90 leading-snug">{note}</div>}
    </div>
  );
};
