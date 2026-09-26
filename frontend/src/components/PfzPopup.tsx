import React, { useState } from 'react';
import { X, MessageSquare, Anchor, Waves } from 'lucide-react';
import { PfzRow } from '../types';
import { TFunc, CONFIDENCE_COLORS } from '../i18n';
import { Units, distRange, seaDepthRange, coordText, distUnitLabel, depthUnitLabel, depthText } from '../pfzFormat';
import { ProfileMiniChart } from './ProfileMiniChart';

interface PfzPopupProps {
  row: PfzRow;
  depths: number[];
  units: Units;
  t: TFunc;
  showGear: boolean;
  speciesName: string | null;
  onMessage: () => void;
  onClose: () => void;
}

const Item: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="flex justify-between gap-3 py-[3px]">
    <span className="text-slate-500">{label}</span>
    <span className="text-slate-100 text-right font-mono">{children}</span>
  </div>
);

/** Marker detail card: INCOIS advisory and OceanEmbed additions, clearly separated. */
export const PfzPopup: React.FC<PfzPopupProps> = ({ row, depths, units, t, showGear, speciesName, onMessage, onClose }) => {
  const [deep, setDeep] = useState(false);
  const na = t('na');
  const level = row.confidence_level;

  return (
    <div
      className="copernicus-panel p-4 text-[11px] flex flex-col gap-3 pointer-events-auto animate-fade-in"
      style={{ width: 340, backgroundColor: 'rgba(12, 20, 35, 0.96)', maxHeight: '100%', overflowY: 'auto' }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-semibold text-white">{row.landmark}</span>
        <button type="button" onClick={onClose} className="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10" title={t('btn.close')}>
          <X size={14} />
        </button>
      </div>

      {/* 1. INCOIS PFZ advisory */}
      <section className="rounded-lg border border-sky-400/20 bg-sky-400/[0.04] px-3 py-2">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-semibold text-sky-300 mb-1">
          <Anchor size={11} /> {t('popup.incois')}
        </div>
        <Item label={t('popup.landmark')}>{row.landmark}</Item>
        <Item label={t('popup.direction')}>
          {t(`direction.${row.direction}`)} / {row.bearing_deg ?? '—'}°
        </Item>
        <Item label={t('popup.distance')}>
          {distRange(row, units.dist)} {distUnitLabel(units.dist)}
        </Item>
        <Item label={t('popup.sea_depth')}>
          {seaDepthRange(row, units.depth)} {depthUnitLabel(units.depth)}
        </Item>
        <Item label={t('popup.position')}>
          {coordText(row, 'lat', units.coord)}, {coordText(row, 'lon', units.coord)}
        </Item>
      </section>

      {/* 2. OceanEmbed subsurface information */}
      <section className="rounded-lg border border-[#4fd1c5]/25 bg-[#4fd1c5]/[0.05] px-3 py-2">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-semibold text-[#4fd1c5] mb-1">
          <Waves size={11} /> {t('popup.oe')}
        </div>
        <Item label={t('popup.d20')}>{depthText(row.d20_m) ?? na}</Item>
        <Item label={t('popup.mld')}>{depthText(row.mld_m) ?? na}</Item>
        <Item label={t('popup.front')}>{row.subsurface_front === null ? na : row.subsurface_front ? t('yes') : t('no')}</Item>
        <Item label={t('popup.confidence')}>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: CONFIDENCE_COLORS[level] }} />
            {level === 'not_available' ? t('msg.conf_na') : `${t(`confidence.${level}`)} (${row.confidence?.toFixed(2)})`}
          </span>
        </Item>
        {showGear && (
          <Item label={`${t('popup.gear')}${speciesName ? ` (${speciesName})` : ''}`}>
            {row.gear_depth_from_m !== null ? `${Math.round(row.gear_depth_from_m)}–${Math.round(row.gear_depth_to_m ?? 0)} m` : na}
          </Item>
        )}
        {row.grid_cell_lat !== null && (
          <Item label={t('popup.grid_cell')}>
            {row.grid_cell_lat.toFixed(2)}°N, {row.grid_cell_lon?.toFixed(2)}°E
          </Item>
        )}
        {row.note && <div className="text-amber-300 mt-1">{row.note}</div>}

        {row.profile && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
              <span>{t('popup.profile')}</span>
              <button type="button" onClick={() => setDeep(!deep)} className="text-[#4fd1c5] hover:underline">
                {deep ? t('btn.show_300') : t('btn.show_1000')}
              </button>
            </div>
            <ProfileMiniChart depths={depths} temps={row.profile} d20={row.d20_m} mld={row.mld_m} maxDepth={deep ? 1000 : 300} />
          </div>
        )}

        <div className="mt-2 text-[11px] leading-relaxed text-slate-200 bg-black/20 rounded-md px-2 py-1.5 select-text">{row.summary_text}</div>
      </section>

      <div className="text-[9.5px] text-slate-500 leading-snug">{t('popup.note')}</div>

      <button
        type="button"
        onClick={onMessage}
        className="self-start px-3 py-1.5 rounded-lg text-[11px] font-medium flex items-center gap-1.5 bg-gradient-to-r from-[#4fd1c5]/20 to-[#38bdf8]/15 text-[#4fd1c5] border border-[#4fd1c5]/35 hover:from-[#4fd1c5]/30"
      >
        <MessageSquare size={12} />
        {t('btn.message')}
      </button>
    </div>
  );
};
