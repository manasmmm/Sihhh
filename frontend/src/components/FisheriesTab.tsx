import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Download, Loader2, Info, AlertTriangle, GripHorizontal } from 'lucide-react';
import { DerivedVar, Language, PfzEnriched, PfzSector, Species } from '../types';
import { fetchLanguages, fetchPfzEnriched, fetchPfzSectors, fetchSpecies, pfzCsvUrl, downloadFile } from '../api';
import { TFunc, CONFIDENCE_COLORS, formatDate } from '../i18n';
import { Units } from '../pfzFormat';
import { FisheriesMap } from './FisheriesMap';
import { AdvisoryTable } from './AdvisoryTable';
import { PfzPopup } from './PfzPopup';
import { DerivedLegend } from './DerivedLegend';
import { FishermanMessageModal } from './FishermanMessageModal';
import { BASEMAPS, BasemapId } from '../basemaps';

interface FisheriesTabProps {
  depths: number[];
  lang: string;
  onLangChange: (lang: string) => void;
  t: TFunc;
  isDraft: boolean;
  onDateChange: (date: string | null) => void;
  basemap: BasemapId;
  onBasemapChange: (id: BasemapId) => void;
}

type BgLayer = DerivedVar | 'none';
const BG_LAYERS: BgLayer[] = ['d20', 'mld', 'front_50m', 'front_100m', 'subsurface_front_flag', 'confidence', 'none'];
const MAX_MESSAGE_CHARS = 320;

const Segmented: React.FC<{
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}> = ({ options, value, onChange }) => (
  <div className="inline-flex rounded-lg bg-white/[0.04] border border-white/10 p-0.5">
    {options.map((o) => (
      <button
        key={o.value}
        type="button"
        onClick={() => onChange(o.value)}
        className={`px-2 py-0.5 rounded-md text-[10.5px] font-medium transition-colors ${
          value === o.value ? 'bg-[#4fd1c5]/20 text-[#4fd1c5]' : 'text-slate-400 hover:text-slate-200'
        }`}
      >
        {o.label}
      </button>
    ))}
  </div>
);

const Control: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <label className="flex flex-col gap-1">
    <span className="text-[9.5px] uppercase tracking-wider text-slate-500 font-semibold">{label}</span>
    {children}
  </label>
);

const selectCls =
  'bg-[#0b1322] border border-white/10 rounded-lg px-2 py-1 text-[11px] text-slate-100 focus:outline-none focus:border-[#4fd1c5]/50';

export const FisheriesTab: React.FC<FisheriesTabProps> = ({
  depths,
  lang,
  onLangChange,
  t,
  isDraft,
  onDateChange,
  basemap,
  onBasemapChange,
}) => {
  const [sectors, setSectors] = useState<PfzSector[]>([]);
  const [sectorCode, setSectorCode] = useState<string>('GOA');
  const [date, setDate] = useState<string | null>(null);
  const [bg, setBg] = useState<BgLayer>('d20');
  const [species, setSpecies] = useState<Species[]>([]);
  const [speciesName, setSpeciesName] = useState<string>('');
  const [languages, setLanguages] = useState<Language[]>([]);
  const [units, setUnits] = useState<Units>({ dist: 'km', depth: 'm', coord: 'dms' });
  const [data, setData] = useState<PfzEnriched | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [messageIdx, setMessageIdx] = useState<number | null>(null);
  const [panelHeight, setPanelHeight] = useState<number>(250);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const dragRef = useRef<{ y: number; h: number } | null>(null);

  // Static lists
  useEffect(() => {
    fetchPfzSectors()
      .then((r) => {
        setSectors(r.sectors);
        setSectorCode(r.default);
      })
      .catch((e) => setError(e.message));
    fetchSpecies()
      .then((r) => setSpecies(r.species))
      .catch(() => setSpecies([]));
    fetchLanguages()
      .then((r) => setLanguages(r.languages))
      .catch(() => setLanguages([]));
  }, []);

  const sector = useMemo(() => sectors.find((s) => s.code === sectorCode) ?? null, [sectors, sectorCode]);
  const allPfzDates = useMemo(() => Array.from(new Set(sectors.flatMap((s) => s.dates))).sort(), [sectors]);
  const configuredSpecies = species.filter((s) => s.configured);

  // Pick the latest date that has an advisory for this sector
  useEffect(() => {
    if (!sector) return;
    if (sector.dates.length === 0) setDate(null);
    else if (!date || !sector.dates.includes(date)) setDate(sector.dates[sector.dates.length - 1]);
  }, [sector]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => onDateChange(date), [date, onDateChange]);

  // Enriched advisory
  useEffect(() => {
    if (!sector || !date) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchPfzEnriched(sector.code, date, speciesName || null, lang)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setSelected((s) => (s !== null && s < d.rows.length ? s : null));
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [sector, date, speciesName, lang]);

  const rows = data?.rows ?? [];
  const showGear = !!(speciesName && data?.species?.configured);
  const selectedRow = selected !== null ? rows[selected] ?? null : null;
  const confAvailable = rows.some((r) => r.confidence_level !== 'not_available');
  const handleSelect = useCallback((i: number) => setSelected(i), []);

  const onDragStart = (e: React.MouseEvent) => {
    dragRef.current = { y: e.clientY, h: panelHeight };
    const move = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const h = dragRef.current.h + (dragRef.current.y - ev.clientY);
      setPanelHeight(Math.max(90, Math.min(window.innerHeight * 0.7, h)));
    };
    const up = () => {
      dragRef.current = null;
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  const handleCsv = async () => {
    if (!sector || !date) return;
    setDownloadError(null);
    try {
      await downloadFile(pfzCsvUrl(sector.code, date, speciesName || null, lang), `pfz_enriched_${sector.code}_${date}.csv`);
    } catch (e: any) {
      setDownloadError(e.message);
    }
  };

  const noDatesForSector = sector !== null && sector.dates.length === 0;

  return (
    <div className="w-full h-full flex flex-col bg-[#060a10] text-slate-100">
      {/* Controls bar */}
      <div className="flex flex-wrap items-end gap-x-4 gap-y-2 px-4 py-2.5 border-b border-white/[0.06]" style={{ backgroundColor: 'rgba(12, 20, 35, 0.92)' }}>
        <Control label={t('fish.sector')}>
          <select className={selectCls} value={sectorCode} onChange={(e) => setSectorCode(e.target.value)}>
            {sectors.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name}
                {s.dates.length ? '' : ' (—)'}
              </option>
            ))}
          </select>
        </Control>

        <Control label={t('fish.date')}>
          <select className={selectCls} value={date ?? ''} onChange={(e) => setDate(e.target.value)} disabled={noDatesForSector}>
            {noDatesForSector && <option value="">—</option>}
            {allPfzDates.map((d) => (
              <option key={d} value={d} disabled={!sector?.dates.includes(d)}>
                {formatDate(d)}
              </option>
            ))}
          </select>
        </Control>

        <Control label={t('fish.background')}>
          <select className={selectCls} value={bg} onChange={(e) => setBg(e.target.value as BgLayer)}>
            {BG_LAYERS.map((l) => (
              <option key={l} value={l}>
                {t(`bg.${l}`)}
              </option>
            ))}
          </select>
        </Control>

        <Control label={t('fish.basemap')}>
          <select className={selectCls} value={basemap} onChange={(e) => onBasemapChange(e.target.value as BasemapId)}>
            {BASEMAPS.map((b) => (
              <option key={b.id} value={b.id}>
                {b.label}
              </option>
            ))}
          </select>
        </Control>

        {configuredSpecies.length > 0 ? (
          <Control label={t('fish.species')}>
            <select className={selectCls} value={speciesName} onChange={(e) => setSpeciesName(e.target.value)}>
              <option value="">{t('fish.species_none')}</option>
              {configuredSpecies.map((s) => (
                <option key={s.name} value={s.name}>
                  {t(`species.${s.name}`) === `species.${s.name}` ? s.name : t(`species.${s.name}`)}
                </option>
              ))}
            </select>
          </Control>
        ) : (
          <div className="text-[10px] text-slate-500 self-center max-w-[140px] leading-tight" title="config/species.json">
            {t('msg.species_not_configured')}
          </div>
        )}

        <Control label={t('fish.distance')}>
          <Segmented
            options={[
              { value: 'km', label: 'km' },
              { value: 'nm', label: 'nm' },
            ]}
            value={units.dist}
            onChange={(v) => setUnits({ ...units, dist: v as Units['dist'] })}
          />
        </Control>
        <Control label={t('fish.sea_depth')}>
          <Segmented
            options={[
              { value: 'm', label: 'm' },
              { value: 'fathom', label: 'fathoms' },
            ]}
            value={units.depth}
            onChange={(v) => setUnits({ ...units, depth: v as Units['depth'] })}
          />
        </Control>
        <Control label={t('fish.coords')}>
          <Segmented
            options={[
              { value: 'dms', label: 'DMS' },
              { value: 'decimal', label: 'Decimal' },
            ]}
            value={units.coord}
            onChange={(v) => setUnits({ ...units, coord: v as Units['coord'] })}
          />
        </Control>

        <Control label={t('fish.language')}>
          <select className={selectCls} value={lang} onChange={(e) => onLangChange(e.target.value)}>
            {(languages.length ? languages : [{ code: 'en', name: 'English', status: 'final' }]).map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </Control>
        {isDraft && (
          <span className="self-center text-[10px] px-2 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/25">
            {t('fish.draft_note')}
          </span>
        )}
      </div>

      {/* Map */}
      <div className="relative flex-1 min-h-0">
        <FisheriesMap
          date={data?.oceanembed_available ? date : null}
          layer={bg}
          bbox={sector?.bbox ?? null}
          rows={rows}
          selected={selected}
          onSelect={handleSelect}
          basemap={basemap}
        />

        {/* Status messages */}
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] flex flex-col items-center gap-2 pointer-events-none">
          {loading && (
            <div className="px-3 py-1.5 rounded-lg bg-slate-900/90 border border-[#4fd1c5]/30 text-[11px] text-[#4fd1c5] flex items-center gap-2">
              <Loader2 size={13} className="animate-spin" /> {t('msg.loading')}
            </div>
          )}
          {noDatesForSector && (
            <div className="px-3 py-1.5 rounded-lg bg-amber-950/90 border border-amber-500/30 text-[11px] text-amber-200 flex items-center gap-2">
              <Info size={13} /> {t('msg.no_dates', { sector: sectorCode })}
            </div>
          )}
          {!loading && data && data.message && (
            <div className="px-3 py-1.5 rounded-lg bg-amber-950/90 border border-amber-500/30 text-[11px] text-amber-200 flex items-center gap-2 max-w-xl">
              <Info size={13} /> {data.rows.length === 0 ? t('msg.no_pfz') : data.message}
            </div>
          )}
          {error && (
            <div className="px-3 py-1.5 rounded-lg bg-rose-950/90 border border-rose-500/30 text-[11px] text-rose-200 flex items-center gap-2">
              <AlertTriangle size={13} /> {t('msg.error')}: {error}
            </div>
          )}
          {data && data.problems.length > 0 && (
            <div className="px-3 py-1.5 rounded-lg bg-rose-950/90 border border-rose-500/30 text-[10.5px] text-rose-200 max-w-xl font-mono">
              {data.problems.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </div>
          )}
        </div>

        {/* Legend */}
        <div className="absolute bottom-3 left-3 z-[1000] flex flex-col gap-2">
          {bg !== 'none' && data?.oceanembed_available && (
            <DerivedLegend
              variable={bg}
              title={t(`bg.${bg}`)}
              width={260}
              note={bg === 'confidence' && !confAvailable ? t('msg.conf_na') : null}
              labels={{
                thresholdTemplate: t('legend.threshold'),
                ssfYes: t('legend.ssf_yes'),
                ssfNo: t('legend.ssf_no'),
                confidenceNote: t('legend.confidence_note'),
              }}
            />
          )}
          <div className="copernicus-panel px-3 py-2 text-[10px] flex flex-wrap gap-x-3 gap-y-1 pointer-events-auto" style={{ width: 260, backgroundColor: 'rgba(12, 20, 35, 0.92)' }}>
            <span className="text-slate-500 w-full">{t('legend.markers')}</span>
            {(['high', 'medium', 'low', 'not_available'] as const).map((l) => (
              <span key={l} className="flex items-center gap-1 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full border border-white/70" style={{ background: CONFIDENCE_COLORS[l] }} />
                {t(`confidence.${l}`)}
              </span>
            ))}
            {!confAvailable && rows.length > 0 && <span className="w-full text-amber-300/90">{t('msg.conf_na')}</span>}
          </div>
        </div>

        {/* Marker popup */}
        {selectedRow && (
          <div className="absolute top-3 right-3 bottom-3 z-[1000] flex items-start pointer-events-none">
            <PfzPopup
              row={selectedRow}
              depths={depths}
              units={units}
              t={t}
              showGear={showGear}
              speciesName={speciesName || null}
              onMessage={() => setMessageIdx(selected)}
              onClose={() => setSelected(null)}
            />
          </div>
        )}
      </div>

      {/* Resizable advisory table panel */}
      <div className="flex flex-col border-t border-[#4fd1c5]/15" style={{ height: panelHeight, backgroundColor: 'rgba(12, 20, 35, 0.97)' }}>
        <div onMouseDown={onDragStart} className="h-3 flex items-center justify-center cursor-row-resize text-slate-600 hover:text-slate-400" title="Drag to resize">
          <GripHorizontal size={14} />
        </div>
        <div className="flex items-center justify-between px-4 pb-1.5">
          <span className="text-[11px] text-slate-300 font-medium">
            {data?.sector_name ?? sector?.name ?? ''}
            {date ? ` · ${formatDate(date)}` : ''}
            {rows.length > 0 && <span className="text-slate-500"> · {t('fish.rows', { n: rows.length })}</span>}
          </span>
          <div className="flex items-center gap-2">
            {downloadError && <span className="text-[10px] text-rose-300">{downloadError}</span>}
            <button
              type="button"
              onClick={handleCsv}
              disabled={rows.length === 0}
              className="px-2.5 py-1 rounded-lg text-[10.5px] font-medium flex items-center gap-1.5 bg-white/[0.05] text-slate-300 hover:bg-white/[0.1] hover:text-white border border-white/10 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Download size={12} />
              {t('btn.download_csv')}
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto px-2 pb-2">
          {rows.length > 0 ? (
            <AdvisoryTable rows={rows} units={units} t={t} showGear={showGear} selected={selected} onSelect={handleSelect} onMessage={setMessageIdx} />
          ) : (
            <div className="h-full flex items-center justify-center text-[11px] text-slate-500">
              {loading ? t('msg.loading') : noDatesForSector ? t('msg.no_dates', { sector: sectorCode }) : t('msg.no_pfz')}
            </div>
          )}
        </div>
      </div>

      {messageIdx !== null && rows[messageIdx] && (
        <FishermanMessageModal
          text={rows[messageIdx].summary_text}
          landmark={rows[messageIdx].landmark}
          maxChars={MAX_MESSAGE_CHARS}
          t={t}
          isDraft={isDraft}
          onClose={() => setMessageIdx(null)}
        />
      )}
    </div>
  );
};
