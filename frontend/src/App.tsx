import React, { useState, useEffect, useCallback } from 'react';
import {
  Waves,
  Eye,
  Activity,
  Info,
  Trash2,
  Anchor,
} from 'lucide-react';
import { MapView } from './components/MapView';
import { DepthSlider } from './components/DepthSlider';
import { TimeSlider } from './components/TimeSlider';
import { PointCard } from './components/PointCard';
import { Colorbar } from './components/Colorbar';
import { BasinAverageModal } from './components/BasinAverageModal';
import { DataSourceBadge } from './components/DataSourceBadge';
import {
  Metadata,
  PinnedPoint,
  ArgoFloat,
  ProfileResponse,
  TimeseriesResponse,
} from './types';
import {
  fetchMetadata,
  fetchProfile,
  fetchTimeseries,
  fetchArgoFloats,
} from './api';

// Distinctive high-contrast colors for pinned points
const PIN_COLORS = [
  '#4fd1c5', // Teal
  '#f59e0b', // Amber
  '#ec4899', // Pink
  '#a855f7', // Purple
  '#10b981', // Emerald
  '#06b6d4', // Cyan
];

export const App: React.FC = () => {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [currentDate, setCurrentDate] = useState<string>('2025-01-15');
  const [currentDepth, setCurrentDepth] = useState<number>(0);
  const [pinnedPoints, setPinnedPoints] = useState<PinnedPoint[]>([]);
  const [argoFloats, setArgoFloats] = useState<ArgoFloat[]>([]);
  const [showArgoFloats, setShowArgoFloats] = useState<boolean>(false);
  const [showBasinAverage, setShowBasinAverage] = useState<boolean>(false);
  const [overlayOpacity, setOverlayOpacity] = useState<number>(0.85);
  const [adaptiveColor, setAdaptiveColor] = useState<boolean>(true);
  const [landAlert, setLandAlert] = useState<{ message: string; lat: number; lon: number } | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Load metadata and Argo floats on mount
  useEffect(() => {
    Promise.all([fetchMetadata(), fetchArgoFloats()])
      .then(([meta, argoRes]) => {
        setMetadata(meta);
        if (meta.dates.all_dates && meta.dates.all_dates.length > 0) {
          setCurrentDate(meta.dates.all_dates[0]);
        }
        if (meta.depths_m && meta.depths_m.length > 0) {
          setCurrentDepth(meta.depths_m[0]);
        }
        setArgoFloats(argoRes.floats);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Failed to initialize app:', err);
        setIsLoading(false);
      });
  }, []);

  // Update profile and timeseries when depth or date changes for all open pins
  useEffect(() => {
    if (pinnedPoints.length === 0) return;

    pinnedPoints.forEach((pin) => {
      // Re-fetch profile if date changed
      if (!pin.profile || pin.profile.date !== currentDate) {
        fetchProfile(pin.snapped.lat, pin.snapped.lon, currentDate)
          .then((prof: ProfileResponse) => {
            setPinnedPoints((prev) =>
              prev.map((p) => (p.id === pin.id ? { ...p, profile: prof, loadingProfile: false } : p))
            );
          })
          .catch((err) => console.error('Failed updating pin profile:', err));
      }

      // Re-fetch timeseries if depth changed
      if (!pin.timeseries || pin.timeseries.depth !== currentDepth) {
        fetchTimeseries(pin.snapped.lat, pin.snapped.lon, currentDepth)
          .then((ts: TimeseriesResponse) => {
            setPinnedPoints((prev) =>
              prev.map((p) => (p.id === pin.id ? { ...p, timeseries: ts, loadingTimeseries: false } : p))
            );
          })
          .catch((err) => console.error('Failed updating pin timeseries:', err));
      }
    });
  }, [currentDate, currentDepth]);

  // Handle map click: inspect ocean point
  const handleMapClick = useCallback(
    async (lat: number, lon: number) => {
      // Prevent exceeding maximum sensible pinned cards for screen real estate
      if (pinnedPoints.length >= 4) {
        // Remove oldest pin if at cap
        setPinnedPoints((prev) => prev.slice(1));
      }

      try {
        // Optimistic fetch profile
        const prof = await fetchProfile(lat, lon, currentDate);
        const ts = await fetchTimeseries(prof.snapped.lat, prof.snapped.lon, currentDepth);

        // Check if point already pinned
        const existingIdx = pinnedPoints.findIndex(
          (p) =>
            Math.abs(p.snapped.lat - prof.snapped.lat) < 0.05 &&
            Math.abs(p.snapped.lon - prof.snapped.lon) < 0.05
        );
        if (existingIdx >= 0) return;

        const newPoint: PinnedPoint = {
          id: `pin-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
          color: PIN_COLORS[pinnedPoints.length % PIN_COLORS.length],
          snapped: prof.snapped,
          requested: prof.requested,
          profile: prof,
          timeseries: ts,
          loadingProfile: false,
          loadingTimeseries: false,
        };

        setPinnedPoints((prev) => [...prev, newPoint]);
        setLandAlert(null);
      } catch (err: any) {
        if (err && err.isLandCell) {
          // Graceful land cell message
          setLandAlert({
            message: 'No ocean data over land point',
            lat: err.snapped?.lat ?? lat,
            lon: err.snapped?.lon ?? lon,
          });
          // Auto-hide alert after 3 seconds
          setTimeout(() => setLandAlert(null), 3500);
        } else {
          console.error('Error fetching point inspection:', err);
        }
      }
    },
    [pinnedPoints, currentDate, currentDepth]
  );

  const handleRemovePin = useCallback((id: string) => {
    setPinnedPoints((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const handleClearAllPins = useCallback(() => {
    setPinnedPoints([]);
  }, []);

  if (isLoading || !metadata) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-[#060a10] text-slate-200">
        <div className="relative mb-6">
          <div className="absolute inset-0 rounded-full bg-[#4fd1c5]/10 blur-2xl animate-pulse" style={{ width: 80, height: 80, margin: '-16px' }} />
          <Waves className="w-14 h-14 text-[#4fd1c5] animate-float-wave relative z-10" />
        </div>
        <div className="text-lg font-semibold tracking-wide bg-gradient-to-r from-[#4fd1c5] to-[#38bdf8] bg-clip-text text-transparent">
          OceanEmbed Viewer
        </div>
        <div className="text-xs text-slate-500 font-mono mt-2 tracking-wider">
          Initializing North Indian Ocean reconstruction domain...
        </div>
        <div className="mt-5 w-48 h-1 rounded-full bg-slate-800 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-[#4fd1c5] to-[#38bdf8] animate-pulse" style={{ width: '65%' }} />
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#060a10] text-slate-100">
      {/* 1. Base Map Layer */}
      <MapView
        currentDate={currentDate}
        currentDepth={currentDepth}
        pinnedPoints={pinnedPoints}
        argoFloats={argoFloats}
        showArgoFloats={showArgoFloats}
        adaptiveColor={adaptiveColor}
        onMapClick={handleMapClick}
        onRemovePin={handleRemovePin}
        overlayOpacity={overlayOpacity}
      />

      {/* 2. Top-Left Layer-Info Panel */}
      <div
        className="absolute top-4 left-4 z-[1000] copernicus-panel p-4 text-xs flex flex-col gap-2.5 pointer-events-auto"
        style={{
          width: '320px',
          backgroundColor: 'rgba(12, 20, 35, 0.92)',
        }}
      >
        {/* Header with gradient accent bar */}
        <div className="flex items-center justify-between pb-2.5 relative">
          <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-[#4fd1c5]/40 via-[#38bdf8]/30 to-transparent" />
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-gradient-to-br from-[#4fd1c5]/25 to-[#38bdf8]/15 text-[#4fd1c5] border border-[#4fd1c5]/20">
              <Waves size={18} />
            </div>
            <div>
              <div className="font-bold text-sm tracking-wide text-white flex items-center gap-2">
                <span className="bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                  OceanEmbed Viewer
                </span>
                <span className="text-[8px] px-1.5 py-0.5 rounded-md bg-gradient-to-r from-[#4fd1c5]/20 to-[#38bdf8]/15 text-[#4fd1c5] font-mono border border-[#4fd1c5]/30 font-medium">
                  SIH26066
                </span>
              </div>
              <div className="text-[10px] text-slate-500 font-mono mt-0.5 flex gap-2 items-center">
                Vision Transformer (ViT)
                {metadata && (
                  <DataSourceBadge 
                    dataSource={metadata.data_source || 'mock'} 
                    modelVersion={metadata.model_version || 'unknown'} 
                  />
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Active Layer Details */}
        <div className="flex flex-col gap-2 py-1">
          <div className="flex justify-between items-center">
            <span className="text-slate-500 text-[11px]">Variable</span>
            <span className="font-semibold text-white text-[11px]">
              {metadata.variable.long_name}
              <span className="text-slate-400 font-normal ml-1">({metadata.variable.name})</span>
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500 text-[11px]">Depth Layer</span>
            <span className="font-mono text-[#4fd1c5] font-bold text-xs px-2 py-0.5 rounded-md bg-[#4fd1c5]/10 border border-[#4fd1c5]/20">
              {currentDepth} m
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500 text-[11px]">Timestamp</span>
            <span className="font-mono text-white text-[11px]">{currentDate}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500 text-[11px]">Domain</span>
            <span className="font-mono text-[10px] text-slate-400">
              5°–30°N, 45°–105°E (0.25°)
            </span>
          </div>
        </div>

        {/* Feature Toggles */}
        <div className="pt-2.5 flex items-center justify-between gap-1.5 relative">
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/8 to-transparent" />
          <button
            type="button"
            onClick={() => setShowBasinAverage(!showBasinAverage)}
            title="Toggle Basin-Average time series chart"
            className={`px-2.5 py-1.5 rounded-lg text-[10px] font-medium flex items-center gap-1.5 transition-all duration-200 ${
              showBasinAverage
                ? 'bg-gradient-to-r from-[#4fd1c5]/20 to-[#38bdf8]/15 text-[#4fd1c5] border border-[#4fd1c5]/35 shadow-sm shadow-[#4fd1c5]/10'
                : 'bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-slate-200 border border-transparent'
            }`}
          >
            <Activity size={12} />
            <span>Basin Mean</span>
          </button>

          <button
            type="button"
            onClick={() => setShowArgoFloats(!showArgoFloats)}
            title="Overlay Gridded Argo float validation points"
            className={`px-2.5 py-1.5 rounded-lg text-[10px] font-medium flex items-center gap-1.5 transition-all duration-200 ${
              showArgoFloats
                ? 'bg-gradient-to-r from-[#38bdf8]/20 to-[#3b82f6]/15 text-[#38bdf8] border border-[#38bdf8]/35 shadow-sm shadow-[#38bdf8]/10'
                : 'bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-slate-200 border border-transparent'
            }`}
          >
            <Eye size={12} />
            <span>Argo Truth ({argoFloats.length})</span>
          </button>

          {pinnedPoints.length > 0 && (
            <button
              type="button"
              onClick={handleClearAllPins}
              title="Clear all inspection pins"
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-200"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>

        {/* Opacity slider */}
        <div className="flex items-center gap-2.5 text-[10px] text-slate-500 pt-1.5">
          <Anchor size={10} className="text-slate-600 flex-shrink-0" />
          <span className="flex-shrink-0">Opacity</span>
          <input
            type="range"
            min={0.2}
            max={1.0}
            step={0.05}
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(parseFloat(e.target.value))}
            className="w-full"
          />
          <span className="font-mono text-slate-300 w-8 text-right font-medium">
            {Math.round(overlayOpacity * 100)}%
          </span>
        </div>
      </div>

      {/* 3. Floating Pinned Inspection Cards */}
      <div
        className="absolute top-4 right-24 z-[1000] flex gap-3 pointer-events-none max-h-[88vh] overflow-x-auto overflow-y-auto pr-2"
        style={{ maxWidth: 'calc(100vw - 420px)' }}
      >
        {pinnedPoints.map((point) => (
          <PointCard
            key={point.id}
            point={point}
            currentDate={currentDate}
            currentDepth={currentDepth}
            onClose={handleRemovePin}
          />
        ))}

        {/* Basin Average Modal if toggled */}
        {showBasinAverage && (
          <BasinAverageModal
            currentDepth={currentDepth}
            currentDate={currentDate}
            onClose={() => setShowBasinAverage(false)}
          />
        )}
      </div>

      {/* 4. Vertical Depth Control */}
      <div className="absolute top-20 right-4 z-[1000] pointer-events-auto">
        <DepthSlider
          depths={metadata.depths_m}
          currentDepth={currentDepth}
          onDepthChange={(d) => setCurrentDepth(d)}
        />
      </div>

      {/* 5. Colorbar / Legend */}
      <div className="absolute bottom-28 right-4 z-[1000]">
        <Colorbar
          vmin={
            adaptiveColor
              ? currentDepth === 0
                ? 24
                : currentDepth <= 50
                ? 20
                : currentDepth <= 100
                ? 15
                : currentDepth <= 200
                ? 12
                : currentDepth <= 500
                ? 8
                : 5
              : metadata.variable.colorbar_range[0]
          }
          vmax={
            adaptiveColor
              ? currentDepth === 0
                ? 32
                : currentDepth <= 50
                ? 30
                : currentDepth <= 100
                ? 27
                : currentDepth <= 200
                ? 20
                : currentDepth <= 500
                ? 14
                : 9
              : metadata.variable.colorbar_range[1]
          }
          unit={metadata.variable.units}
          variableName="thetao"
          adaptiveColor={adaptiveColor}
          onToggleAdaptive={() => setAdaptiveColor(!adaptiveColor)}
          currentDepth={currentDepth}
        />
      </div>

      {/* 6. Horizontal Time Slider */}
      <div
        className="absolute bottom-4 left-4 z-[1000] pointer-events-auto"
        style={{ width: 'calc(100vw - 320px)', maxWidth: '980px' }}
      >
        <TimeSlider
          dates={metadata.dates.all_dates}
          currentDate={currentDate}
          onDateChange={(d) => setCurrentDate(d)}
        />
      </div>

      {/* 7. Land Click Toast */}
      {landAlert && (
        <div
          className="absolute bottom-28 left-1/2 -translate-x-1/2 z-[1050] px-5 py-2.5 rounded-xl bg-amber-950/90 text-amber-200 border border-amber-500/30 shadow-xl backdrop-blur-xl text-xs font-mono flex items-center gap-2.5 animate-fade-in"
        >
          <Info size={15} className="text-amber-400" />
          <span>
            {landAlert.message} — snapped to {landAlert.lat.toFixed(2)}°N, {landAlert.lon.toFixed(2)}°E
          </span>
        </div>
      )}
    </div>
  );
};

export default App;
