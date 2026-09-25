import React from 'react';
import { ChevronUp, ChevronDown, Layers } from 'lucide-react';

interface DepthSliderProps {
  depths: number[];
  currentDepth: number;
  onDepthChange: (depth: number) => void;
}

export const DepthSlider: React.FC<DepthSliderProps> = ({
  depths,
  currentDepth,
  onDepthChange,
}) => {
  const currentIndex = depths.indexOf(currentDepth);
  const validIndex = currentIndex >= 0 ? currentIndex : 0;

  const handleStepUp = () => {
    if (validIndex > 0) {
      onDepthChange(depths[validIndex - 1]);
    }
  };

  const handleStepDown = () => {
    if (validIndex < depths.length - 1) {
      onDepthChange(depths[validIndex + 1]);
    }
  };

  // Depths to explicitly show label for
  const labeledDepths = [0, 50, 100, 200, 500, 1000];

  return (
    <div
      className="copernicus-panel flex flex-col items-center select-none text-slate-200"
      style={{
        padding: '14px 12px',
        width: '88px',
        backgroundColor: 'rgba(12, 20, 35, 0.92)',
      }}
    >
      {/* Header */}
      <div className="flex flex-col items-center gap-1.5 mb-3">
        <div className="flex items-center gap-1 text-[10px] font-semibold text-[#4fd1c5] tracking-widest uppercase">
          <Layers size={12} />
          <span>Depth</span>
        </div>
        <div
          className="text-xs font-mono font-bold px-2.5 py-1 rounded-lg text-white"
          style={{
            background: 'linear-gradient(135deg, rgba(79, 209, 197, 0.15), rgba(56, 189, 248, 0.1))',
            border: '1px solid rgba(79, 209, 197, 0.25)',
            boxShadow: '0 0 12px rgba(79, 209, 197, 0.08)',
          }}
        >
          {currentDepth} m
        </div>
      </div>

      {/* Up Button (shallower) */}
      <button
        type="button"
        onClick={handleStepUp}
        disabled={validIndex === 0}
        aria-label="Shallower depth"
        className="p-1.5 rounded-lg text-slate-400 hover:text-[#4fd1c5] hover:bg-[#4fd1c5]/10 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200"
      >
        <ChevronUp size={16} />
      </button>

      {/* Vertical Rail */}
      <div
        className="relative my-2 flex flex-col justify-between items-center"
        style={{ height: '240px', width: '100%' }}
      >
        {/* Central Track Line */}
        <div
          className="absolute left-1/2 -translate-x-1/2 w-[5px] h-full rounded-full"
          style={{
            background: 'linear-gradient(to bottom, #4fd1c5 0%, #38bdf8 30%, #3b82f6 60%, #1e3a8a 100%)',
            opacity: 0.5,
            boxShadow: '0 0 8px rgba(79, 209, 197, 0.1)',
          }}
        />

        {/* Discrete stops */}
        {depths.map((d) => {
          const isSelected = d === currentDepth;
          const isMajor = labeledDepths.includes(d);

          return (
            <div
              key={d}
              onClick={() => onDepthChange(d)}
              className="relative w-full flex items-center justify-between cursor-pointer group py-0.5"
              title={`${d} meters`}
            >
              {/* Depth tick indicator */}
              <div
                className={`z-10 mx-auto rounded-full transition-all duration-200 ${
                  isSelected
                    ? 'w-[18px] h-[18px] bg-white border-[2.5px] border-[#4fd1c5]'
                    : isMajor
                    ? 'w-2.5 h-2.5 bg-slate-400/80 group-hover:bg-[#4fd1c5] group-hover:scale-125'
                    : 'w-[5px] h-[5px] bg-slate-600 group-hover:bg-[#38bdf8]'
                }`}
                style={
                  isSelected
                    ? {
                        boxShadow: '0 0 14px rgba(79, 209, 197, 0.5), 0 0 30px rgba(79, 209, 197, 0.2)',
                      }
                    : undefined
                }
              />

              {/* Label if major stop or selected */}
              {(isMajor || isSelected) && (
                <span
                  className={`absolute right-0.5 text-[9px] font-mono whitespace-nowrap transition-all duration-200 ${
                    isSelected
                      ? 'text-[#4fd1c5] font-bold'
                      : 'text-slate-500 group-hover:text-slate-300'
                  }`}
                >
                  {d}m
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Down Button (deeper) */}
      <button
        type="button"
        onClick={handleStepDown}
        disabled={validIndex === depths.length - 1}
        aria-label="Deeper depth"
        className="p-1.5 rounded-lg text-slate-400 hover:text-[#4fd1c5] hover:bg-[#4fd1c5]/10 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200"
      >
        <ChevronDown size={16} />
      </button>
    </div>
  );
};
