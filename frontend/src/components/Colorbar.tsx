import React from 'react';
import { Sliders, Thermometer } from 'lucide-react';

interface ColorbarProps {
  vmin?: number;
  vmax?: number;
  unit?: string;
  variableName?: string;
  adaptiveColor?: boolean;
  onToggleAdaptive?: () => void;
  currentDepth?: number;
}

export const Colorbar: React.FC<ColorbarProps> = ({
  vmin = 0,
  vmax = 32,
  unit = '°C',
  variableName = 'thetao',
  adaptiveColor = false,
  onToggleAdaptive,
  currentDepth = 0,
}) => {
  // Turbo colormap gradient CSS
  const turboGradient =
    'linear-gradient(to right, #30123b, #4145ab, #4675ed, #39a2fc, #1bcfd4, #24eca6, #61fc6c, #a4fc3b, #d1e834, #f3c63a, #fe9b2d, #f36315, #d93806, #b11901, #7a0402)';

  // Calculate ticks dynamically
  const ticks = React.useMemo(() => {
    const low = vmin;
    const high = vmax;
    const step = (high - low) / 4;
    return [
      Math.round(low),
      Math.round(low + step),
      Math.round(low + step * 2),
      Math.round(low + step * 3),
      Math.round(high),
    ];
  }, [vmin, vmax]);

  return (
    <div
      className="copernicus-panel px-3.5 py-2.5 text-xs flex flex-col gap-2 pointer-events-auto select-none"
      style={{
        width: '280px',
        backgroundColor: 'rgba(12, 20, 35, 0.92)',
      }}
    >
      <div className="flex items-center justify-between text-[11px] font-medium text-slate-300">
        <span className="flex items-center gap-2">
          <Thermometer size={13} className="text-[#4fd1c5]" />
          <span className="text-white font-semibold">{variableName}</span>
          <span className="text-[10px] text-slate-500 font-mono px-1.5 py-0.5 rounded bg-white/[0.04]">
            {currentDepth}m
          </span>
        </span>

        {onToggleAdaptive && (
          <button
            type="button"
            onClick={onToggleAdaptive}
            title={adaptiveColor ? 'Switch to fixed 0-32°C scale' : 'Auto-stretch contrast for this layer'}
            className={`px-2 py-1 rounded-md text-[9px] font-mono flex items-center gap-1 transition-all duration-200 ${
              adaptiveColor
                ? 'bg-gradient-to-r from-[#4fd1c5]/20 to-[#38bdf8]/15 text-[#4fd1c5] border border-[#4fd1c5]/30 font-bold'
                : 'bg-white/[0.06] text-slate-400 hover:text-white border border-transparent hover:border-white/10'
            }`}
          >
            <Sliders size={10} />
            <span>{adaptiveColor ? 'Auto' : '0-32°C'}</span>
          </button>
        )}
      </div>

      {/* Gradient bar with glow */}
      <div className="relative">
        <div
          className="absolute inset-0 rounded-md blur-sm opacity-30"
          style={{ background: turboGradient }}
        />
        <div
          className="relative"
          style={{
            background: turboGradient,
            height: '14px',
            width: '100%',
            borderRadius: '5px',
            boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.4), 0 0 8px rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        />
      </div>

      {/* Ticks */}
      <div className="flex justify-between text-[10px] text-slate-400 font-mono px-0.5">
        {ticks.map((val, idx) => (
          <span key={idx} className={idx === 0 || idx === ticks.length - 1 ? 'text-slate-300 font-medium' : ''}>
            {val}{unit}
          </span>
        ))}
      </div>
    </div>
  );
};
