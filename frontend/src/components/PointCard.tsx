import React, { useRef } from 'react';
import { X, Download, MapPin, Loader2 } from 'lucide-react';
import { PinnedPoint } from '../types';
import { ProfileChart } from './ProfileChart';
import { TimeseriesChart } from './TimeseriesChart';

interface PointCardProps {
  point: PinnedPoint;
  currentDate: string;
  currentDepth: number;
  onClose: (id: string) => void;
}

export const PointCard: React.FC<PointCardProps> = ({
  point,
  currentDate,
  currentDepth,
  onClose,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);

  // Format coordinates cleanly
  const latStr = `${Math.abs(point.snapped.lat).toFixed(2)}°${
    point.snapped.lat >= 0 ? 'N' : 'S'
  }`;
  const lonStr = `${Math.abs(point.snapped.lon).toFixed(2)}°${
    point.snapped.lon >= 0 ? 'E' : 'W'
  }`;

  // Readout current temperature value at selected depth
  let currentTempValue: number | null = null;
  if (point.profile && point.profile.depths_m) {
    const idx = point.profile.depths_m.indexOf(currentDepth);
    if (idx >= 0 && point.profile.temperature_c[idx] !== null) {
      currentTempValue = point.profile.temperature_c[idx];
    }
  }

  // Download chart as image / JSON export
  const handleExport = () => {
    if (!point.profile && !point.timeseries) return;
    const exportData = {
      location: point.snapped,
      current_date: currentDate,
      current_depth: currentDepth,
      current_temperature_c: currentTempValue,
      profile: point.profile,
      timeseries: point.timeseries,
    };
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `oceanembed_${latStr}_${lonStr}_${currentDate}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div
      ref={cardRef}
      className="copernicus-panel flex flex-col gap-3 p-4 text-slate-200 pointer-events-auto animate-fade-in"
      style={{
        width: '370px',
        backgroundColor: 'rgba(12, 20, 35, 0.94)',
        border: `1px solid ${point.color}30`,
        borderRadius: '14px',
        boxShadow: `0 16px 40px rgba(0, 0, 0, 0.6), 0 0 20px ${point.color}12`,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 relative">
        <div className="absolute bottom-0 left-0 right-0 h-[1px]" style={{ background: `linear-gradient(to right, ${point.color}40, transparent)` }} />
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div
              className="absolute inset-0 rounded-full blur-md opacity-50"
              style={{ backgroundColor: point.color }}
            />
            <div
              className="relative w-3.5 h-3.5 rounded-full flex-shrink-0 border-2 border-white/30"
              style={{ backgroundColor: point.color }}
            />
          </div>
          <div className="flex items-center gap-1.5 font-mono text-xs font-semibold text-white">
            <MapPin size={13} className="text-slate-500" />
            <span>
              {latStr}, {lonStr}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleExport}
            title="Export point observation data"
            className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/[0.08] transition-all duration-200"
          >
            <Download size={14} />
          </button>
          <button
            type="button"
            onClick={() => onClose(point.id)}
            title="Close inspection panel"
            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-200"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Big Current Value Readout */}
      <div className="flex items-baseline justify-between px-3 py-2.5 rounded-xl bg-gradient-to-br from-white/[0.04] to-white/[0.02] border border-white/[0.06]">
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-widest text-slate-500 font-semibold">
            Potential Temperature
          </span>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-3xl font-black font-mono tracking-tight text-white">
              {currentTempValue !== null ? `${currentTempValue.toFixed(1)}` : '--'}
            </span>
            <span className="text-sm font-bold text-[#4fd1c5]">°C</span>
          </div>
        </div>

        <div className="flex flex-col items-end text-[10px] font-mono text-slate-500 gap-1">
          <span
            className="px-2 py-0.5 rounded-md font-semibold"
            style={{
              background: 'linear-gradient(135deg, rgba(79, 209, 197, 0.12), rgba(56, 189, 248, 0.08))',
              color: '#4fd1c5',
              border: '1px solid rgba(79, 209, 197, 0.2)',
            }}
          >
            {currentDepth}m
          </span>
          <span className="text-slate-600">{currentDate}</span>
        </div>
      </div>

      {/* Loading state indicator */}
      {(point.loadingProfile || point.loadingTimeseries) && (
        <div className="flex items-center justify-center gap-2 py-4 text-xs text-[#4fd1c5]">
          <Loader2 size={16} className="animate-spin" />
          <span className="font-mono">Updating ocean soundings...</span>
        </div>
      )}

      {/* Chart A: Time Series */}
      {point.timeseries && (
        <div className="pt-2 relative">
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/6 to-transparent" />
          <TimeseriesChart
            timeseries={point.timeseries}
            currentDate={currentDate}
          />
        </div>
      )}

      {/* Chart B: Depth Profile */}
      {point.profile && (
        <div className="pt-2 relative">
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/6 to-transparent" />
          <ProfileChart
            profile={point.profile}
            currentDepth={currentDepth}
          />
        </div>
      )}
    </div>
  );
};
