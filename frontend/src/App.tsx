import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Waves,
  Eye,
  Activity,
  Info,
  Trash2,
  Anchor,
  ShieldCheck,
  Download,
  Upload,
  AlertTriangle,
  Layers,
  Map as MapIcon,
} from 'lucide-react';
import { MapView } from './components/MapView';
import { DepthSlider } from './components/DepthSlider';
import { TimeSlider } from './components/TimeSlider';
import { PointCard } from './components/PointCard';
import { Colorbar } from './components/Colorbar';
import { BasinAverageModal } from './components/BasinAverageModal';
import { TopBar, TabId } from './components/TopBar';
import { ValidationPanel } from './components/ValidationPanel';
import { DerivedLegend } from './components/DerivedLegend';
import { FisheriesTab } from './components/FisheriesTab';
import {
  Metadata,
  PinnedPoint,
  ArgoFloat,
  ProfileResponse,
  TimeseriesResponse,
  MapLayer,
} from './types';
import {
  fetchMeta,
  fetchProfile,
  fetchTimeseries,
  fetchArgoFloats,
  downloadFile,
  netcdfUrl,
  derivedNetcdfUrl,
  uploadModelOutput,
} from './api';
import { useI18n } from './i18n';
import { BASEMAPS, BasemapId, loadBasemapChoice, saveBasemapChoice } from './basemaps';

// Explorer colour-layer options (derived layers are optional in this tab)
const EXPLORER_LAYERS: { value: MapLayer; label: string }[] = [
  { value: 'thetao', label: 'Temperature (thetao) at selected depth' },
  { value: 'd20', label: 'Warm-layer depth (D20)' },
  { value: 'mld', label: 'Mixed-layer depth (MLD)' },
  { value: 'front_0m', label: 'Front strength at 0 m' },
  { value: 'front_50m', label: 'Front strength at 50 m' },
  { value: 'front_100m', label: 'Front strength at 100 m' },
  { value: 'subsurface_front_flag', label: 'Subsurface-only fronts' },
  { value: 'confidence', label: 'Confidence (data density)' },
];

const META_REFRESH_MS = 30000;

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
  const [initError, setInitError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('explorer');
  const [lang, setLang] = useState<string>('en');
  const [fisheriesDate, setFisheriesDate] = useState<string | null>(null);
  const [mapLayer, setMapLayer] = useState<MapLayer>('thetao');
  const [fieldRange, setFieldRange] = useState<[number, number] | null>(null);
  const handleRangeChange = useCallback((vmin: number, vmax: number) => setFieldRange([vmin, vmax]), []);
  const [basemap, setBasemapState] = useState<BasemapId>(loadBasemapChoice);
  const setBasemap = useCallback((id: BasemapId) => {
    setBasemapState(id);
    saveBasemapChoice(id);
  }, []);
  const [showValidation, setShowValidation] = useState<boolean>(false);
  const [toast, setToast] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const { t, isDraft } = useI18n(lang);

  const showToast = useCallback((kind: 'ok' | 'error', text: string) => {
    setToast({ kind, text });
    setTimeout(() => setToast(null), 6000);
  }, []);

  // Load metadata and Argo floats on mount
  useEffect(() => {
    Promise.all([fetchMeta(), fetchArgoFloats().catch(() => ({ count: 0, floats: [] as ArgoFloat[] }))])
      .then(([meta, argoRes]) => {
        setMetadata(meta);
        if (meta.ready_dates && meta.ready_dates.length > 0) {
          // In-backend model: open on a day that is already reconstructed (others take a few seconds)
          setCurrentDate(meta.ready_dates[meta.ready_dates.length - 1]);
        } else if (meta.dates.all_dates && meta.dates.all_dates.length > 0) {
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
        setInitError(err instanceof Error ? err.message : String(err));
        setIsLoading(false);
      });
  }, []);

  // Rescan: model output files dropped into the folder appear without a reload
  const refreshMeta = useCallback(() => {
    fetchMeta()
      .then((meta) => setMetadata(meta))
      .catch((err) => console.error('Metadata refresh failed:', err));
  }, []);
  useEffect(() => {
    if (!metadata) return;
    const id = window.setInterval(refreshMeta, META_REFRESH_MS);
    return () => window.clearInterval(id);
  }, [metadata !== null, refreshMeta]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDownload = useCallback(
    async (kind: 'thetao' | 'derived') => {
      setBusy(kind);
      try {
        if (kind === 'thetao') await downloadFile(netcdfUrl(currentDate), `thetao_${currentDate}.nc`);
        else await downloadFile(derivedNetcdfUrl(currentDate), `derived_${currentDate}.nc`);
      } catch (e: any) {
        showToast('error', `Download failed: ${e.message}`);
      } finally {
        setBusy(null);
      }
    },
    [currentDate, showToast]
  );

  const handleUpload = useCallback(
    async (file: File) => {
      setBusy('upload');
      try {
        const res = await uploadModelOutput(file);
        if (res.saved) {
          const note = metadata?.data_source === 'model_output_files' ? '' : ' (set DATA_SOURCE=files to display it)';
          showToast('ok', `${file.name} validated and saved${note}.${res.warnings.length ? ' Warnings: ' + res.warnings.join('; ') : ''}`);
          refreshMeta();
        } else {
          showToast('error', `${file.name} rejected: ${res.errors.join('; ')}`);
        }
      } catch (e: any) {
        showToast('error', `Upload failed: ${e.message}`);
      } finally {
        setBusy(null);
        if (uploadInputRef.current) uploadInputRef.current.value = '';
      }
    },
    [metadata?.data_source, refreshMeta, showToast]
  );

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

  if (!isLoading && initError) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-[#060a10] text-slate-200 gap-4 px-6">
        <AlertTriangle className="w-12 h-12 text-amber-400" />
        <div className="text-lg font-semibold text-white">OceanEmbed Viewer could not load data</div>
        <div className="max-w-xl text-center text-sm font-mono text-amber-200 bg-amber-950/40 border border-amber-500/30 rounded-xl px-5 py-3">
          {initError}
        </div>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="px-4 py-1.5 rounded-lg text-xs font-medium bg-[#4fd1c5]/15 text-[#4fd1c5] border border-[#4fd1c5]/35"
        >
          Retry
        </button>
      </div>
    );
  }

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
    <div className="w-full h-full flex flex-col overflow-hidden bg-[#060a10] text-slate-100">
      <TopBar
        metadata={metadata}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        productDate={activeTab === 'explorer' ? currentDate : fisheriesDate}
        tabLabels={{ explorer: 'Explorer', fisheries: 'Fisheries Advisory' }}
      />

      {activeTab === 'fisheries' ? (
        <div className="relative flex-1 min-h-0">
          <FisheriesTab
            depths={metadata.depths_m}
            lang={lang}
            onLangChange={setLang}
            t={t}
            isDraft={isDraft}
            onDateChange={setFisheriesDate}
            basemap={basemap}
            onBasemapChange={setBasemap}
          />
        </div>
      ) : (
    <div className="relative flex-1 min-h-0 overflow-hidden">
      {/* 1. Base Map Layer */}
      <MapView
        dates={metadata.dates.all_dates}
        dataVersion={`${metadata.data_source}|${metadata.model_version ?? ''}|${metadata.per_date?.[metadata.dates.end ?? '']?.generated_at ?? ''}`}
        layer={mapLayer}
        onRangeChange={handleRangeChange}
        basemap={basemap}
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

      {/* 2. Top-Left Layer-Info Panel (+ optional validation panel below it) */}
      <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-3 pointer-events-none">
      <div
        className="copernicus-panel p-4 text-xs flex flex-col gap-2.5 pointer-events-auto"
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
              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                Graph Neural Network (GNN-OAM)
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

        {/* Colour layer: thetao (default) or a derived layer */}
        <div className="flex items-center gap-2.5 text-[10px] text-slate-500">
          <Layers size={10} className="text-slate-600 flex-shrink-0" />
          <span className="flex-shrink-0">Layer</span>
          <select
            value={mapLayer}
            onChange={(e) => setMapLayer(e.target.value as MapLayer)}
            className="w-full bg-[#0b1322] border border-white/10 rounded-md px-1.5 py-1 text-[10.5px] text-slate-100 focus:outline-none focus:border-[#4fd1c5]/50"
          >
            {EXPLORER_LAYERS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </div>

        {/* Background map */}
        <div className="flex items-center gap-2.5 text-[10px] text-slate-500">
          <MapIcon size={10} className="text-slate-600 flex-shrink-0" />
          <span className="flex-shrink-0">Map</span>
          <select
            value={basemap}
            onChange={(e) => setBasemap(e.target.value as BasemapId)}
            className="w-full bg-[#0b1322] border border-white/10 rounded-md px-1.5 py-1 text-[10.5px] text-slate-100 focus:outline-none focus:border-[#4fd1c5]/50"
          >
            {BASEMAPS.map((b) => (
              <option key={b.id} value={b.id}>
                {b.label}
              </option>
            ))}
          </select>
        </div>

        {/* Downloads, upload and validation */}
        <div className="pt-2.5 flex flex-wrap items-center gap-1.5 relative">
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/8 to-transparent" />
          <button
            type="button"
            onClick={() => handleDownload('thetao')}
            disabled={busy !== null}
            title={`Download CF-1.8 NetCDF of thetao for ${currentDate}`}
            className="px-2 py-1.5 rounded-lg text-[10px] font-medium flex items-center gap-1.5 bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white border border-white/5 disabled:opacity-50"
          >
            <Download size={11} />
            {busy === 'thetao' ? 'Preparing…' : 'Download NetCDF (thetao)'}
          </button>
          <button
            type="button"
            onClick={() => handleDownload('derived')}
            disabled={busy !== null}
            title={`Download NetCDF of derived layers for ${currentDate}`}
            className="px-2 py-1.5 rounded-lg text-[10px] font-medium flex items-center gap-1.5 bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white border border-white/5 disabled:opacity-50"
          >
            <Download size={11} />
            {busy === 'derived' ? 'Preparing…' : 'Download NetCDF (derived layers)'}
          </button>
          <button
            type="button"
            onClick={() => setShowValidation(!showValidation)}
            className={`px-2 py-1.5 rounded-lg text-[10px] font-medium flex items-center gap-1.5 transition-all duration-200 ${
              showValidation
                ? 'bg-gradient-to-r from-[#4fd1c5]/20 to-[#38bdf8]/15 text-[#4fd1c5] border border-[#4fd1c5]/35'
                : 'bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-slate-200 border border-transparent'
            }`}
          >
            <ShieldCheck size={11} />
            Validation
          </button>
          <button
            type="button"
            onClick={() => uploadInputRef.current?.click()}
            disabled={busy !== null}
            title="Upload one thetao_YYYY-MM-DD.nc or .npy model output file (validated before saving)"
            className="px-2 py-1.5 rounded-lg text-[10px] font-medium flex items-center gap-1.5 bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-slate-200 border border-transparent disabled:opacity-50"
          >
            <Upload size={11} />
            {busy === 'upload' ? 'Uploading…' : 'Upload model output'}
          </button>
          <input
            ref={uploadInputRef}
            type="file"
            accept=".nc,.npy"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
          />
        </div>
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
        {mapLayer !== 'thetao' ? (
          <DerivedLegend
            variable={mapLayer}
            title={EXPLORER_LAYERS.find((l) => l.value === mapLayer)?.label ?? mapLayer}
          />
        ) : (
        <Colorbar
          // Exact range the server used for the image on screen (auto contrast or fixed 0-32)
          vmin={fieldRange ? fieldRange[0] : metadata.variable.colorbar_range[0]}
          vmax={fieldRange ? fieldRange[1] : metadata.variable.colorbar_range[1]}
          unit={metadata.variable.units}
          variableName="thetao"
          adaptiveColor={adaptiveColor}
          onToggleAdaptive={() => setAdaptiveColor(!adaptiveColor)}
          currentDepth={currentDepth}
        />
        )}
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
      )}

      {/* Validation window (centred over the page) */}
      {showValidation && activeTab === 'explorer' && <ValidationPanel onClose={() => setShowValidation(false)} />}

      {/* Download / upload result toast */}
      {toast && (
        <div
          className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-[2500] max-w-2xl px-5 py-2.5 rounded-xl shadow-xl backdrop-blur-xl text-xs font-mono flex items-center gap-2.5 animate-fade-in border ${
            toast.kind === 'ok'
              ? 'bg-emerald-950/90 text-emerald-200 border-emerald-500/30'
              : 'bg-rose-950/90 text-rose-200 border-rose-500/30'
          }`}
          onClick={() => setToast(null)}
        >
          {toast.kind === 'ok' ? <Info size={15} /> : <AlertTriangle size={15} />}
          <span>{toast.text}</span>
        </div>
      )}
    </div>
  );
};

export default App;
