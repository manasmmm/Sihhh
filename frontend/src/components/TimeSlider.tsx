import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  Calendar,
} from 'lucide-react';
import { displayDate } from '../i18n';

interface TimeSliderProps {
  dates: string[];
  currentDate: string;
  onDateChange: (date: string) => void;
}

export const TimeSlider: React.FC<TimeSliderProps> = ({
  dates,
  currentDate,
  onDateChange,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(6); // frames per sec
  const timerRef = useRef<number | null>(null);

  const currentIndex = dates.indexOf(currentDate);
  const validIndex = currentIndex >= 0 ? currentIndex : 0;

  // Format date helper: "2023-01-15" -> "15 Jan 2023"
  const formattedDate = useMemo(() => {
    if (!currentDate) return '';
    try {
      const parts = currentDate.split('-');
      const year = displayDate(currentDate).split('-')[0];
      const monthIndex = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
      ];
      return `${day} ${months[monthIndex]} ${year}`;
    } catch {
      return currentDate;
    }
  }, [currentDate]);

  // Identify month boundary ticks
  const monthTicks = useMemo(() => {
    const ticks: { index: number; label: string; percent: number }[] = [];
    let lastMonth = '';
    dates.forEach((d, idx) => {
      const parts = d.split('-');
      const monthYear = `${parts[0]}-${parts[1]}`;
      if (monthYear !== lastMonth) {
        const monthNum = parseInt(parts[1], 10) - 1;
        const months = [
          'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
        ];
        ticks.push({
          index: idx,
          label: `${months[monthNum]} ${displayDate(d).split('-')[0]}`,
          percent: dates.length > 1 ? (idx / (dates.length - 1)) * 100 : 0,
        });
        lastMonth = monthYear;
      }
    });
    return ticks;
  }, [dates]);

  // Animation player loop
  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.round(1000 / playbackSpeed);
      timerRef.current = window.setInterval(() => {
        onDateChange(dates[(validIndex + 1) % dates.length]);
      }, intervalMs);
    } else if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
      }
    };
  }, [isPlaying, validIndex, playbackSpeed, dates, onDateChange]);

  const handleTogglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleStepPrev = () => {
    setIsPlaying(false);
    if (validIndex > 0) {
      onDateChange(dates[validIndex - 1]);
    }
  };

  const handleStepNext = () => {
    setIsPlaying(false);
    if (validIndex < dates.length - 1) {
      onDateChange(dates[validIndex + 1]);
    }
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsPlaying(false);
    const newIdx = parseInt(e.target.value, 10);
    if (newIdx >= 0 && newIdx < dates.length) {
      onDateChange(dates[newIdx]);
    }
  };

  return (
    <div
      className="copernicus-panel px-4 py-3 text-slate-200 select-none flex flex-col gap-2 pointer-events-auto"
      style={{
        backgroundColor: 'rgba(15, 23, 36, 0.92)',
        border: '1px solid rgba(255, 255, 255, 0.14)',
        borderRadius: '10px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
      }}
    >
      {/* Top control bar: Date display & playback buttons */}
      <div className="flex items-center justify-between gap-4">
        {/* Date Display */}
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-[#4fd1c5]/15 text-[#4fd1c5] border border-[#4fd1c5]/30">
            <Calendar size={16} />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold font-mono text-white tracking-wide">
              {formattedDate}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              Day {validIndex + 1} of {dates.length} • {displayDate(currentDate)}
            </span>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onDateChange(dates[0])}
            title="Start of period"
            className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <SkipBack size={15} />
          </button>
          <button
            type="button"
            onClick={handleStepPrev}
            disabled={validIndex === 0}
            title="Previous day"
            className="p-1.5 rounded text-slate-300 hover:text-white hover:bg-white/10 disabled:opacity-30 transition-colors"
          >
            <ChevronLeft size={17} />
          </button>
          <button
            type="button"
            onClick={handleTogglePlay}
            title={isPlaying ? 'Pause animation' : 'Play evolution animation'}
            className="px-3 py-1.5 rounded-md bg-[#4fd1c5] hover:bg-[#38bdf8] text-slate-950 font-semibold flex items-center gap-1.5 shadow-md shadow-[#4fd1c5]/20 transition-colors"
          >
            {isPlaying ? <Pause size={15} /> : <Play size={15} fill="currentColor" />}
            <span className="text-xs">{isPlaying ? 'Pause' : 'Play'}</span>
          </button>
          <button
            type="button"
            onClick={handleStepNext}
            disabled={validIndex === dates.length - 1}
            title="Next day"
            className="p-1.5 rounded text-slate-300 hover:text-white hover:bg-white/10 disabled:opacity-30 transition-colors"
          >
            <ChevronRight size={17} />
          </button>
          <button
            type="button"
            onClick={() => onDateChange(dates[dates.length - 1])}
            title="End of period"
            className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <SkipForward size={15} />
          </button>

          {/* Speed Selector */}
          <div className="ml-2 flex items-center gap-1 text-[10px] text-slate-400 font-mono">
            <span>Speed:</span>
            {[4, 6, 10].map((spd) => (
              <button
                key={spd}
                type="button"
                onClick={() => setPlaybackSpeed(spd)}
                className={`px-1.5 py-0.5 rounded ${
                  playbackSpeed === spd
                    ? 'bg-[#4fd1c5]/25 text-[#4fd1c5] font-bold border border-[#4fd1c5]/40'
                    : 'hover:text-slate-200'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Timeline Slider with Month Ticks */}
      <div className="relative pt-2 pb-4">
        {/* Month boundary markers */}
        <div className="relative w-full h-3 mb-1">
          {monthTicks.map((mt) => (
            <div
              key={mt.index}
              className="absolute transform -translate-x-1/2 flex flex-col items-center"
              style={{ left: `${mt.percent}%` }}
            >
              <div className="w-[1px] h-2 bg-slate-500/70 mb-0.5" />
              <span className="text-[9px] font-mono text-slate-400 whitespace-nowrap">
                {mt.label}
              </span>
            </div>
          ))}
        </div>

        {/* Range Scrubber */}
        <input
          type="range"
          min={0}
          max={dates.length - 1}
          value={validIndex}
          onChange={handleSliderChange}
          className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-[#4fd1c5] bg-slate-700/60 focus:outline-none"
        />
      </div>
    </div>
  );
};
