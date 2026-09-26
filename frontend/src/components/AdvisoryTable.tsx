import React, { useEffect, useRef } from 'react';
import { MessageSquare } from 'lucide-react';
import { PfzRow } from '../types';
import { TFunc, CONFIDENCE_COLORS } from '../i18n';
import { Units, distRange, seaDepthRange, coordText, distUnitLabel, depthUnitLabel } from '../pfzFormat';

interface AdvisoryTableProps {
  rows: PfzRow[];
  units: Units;
  t: TFunc;
  showGear: boolean;
  selected: number | null;
  onSelect: (idx: number) => void;
  onMessage: (idx: number) => void;
}

const fmtDepth = (v: number | null, na: string) => (v === null ? na : String(Math.round(v)));

/** INCOIS column order first, then the OceanEmbed additions under their own group header. */
export const AdvisoryTable: React.FC<AdvisoryTableProps> = ({ rows, units, t, showGear, selected, onSelect, onMessage }) => {
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);
  const na = '—';
  const oeCols = 4 + (showGear ? 1 : 0);

  useEffect(() => {
    if (selected !== null) rowRefs.current[selected]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [selected]);

  const th = 'px-2.5 py-1.5 font-medium text-left whitespace-nowrap';
  const thOe = `${th} bg-[#4fd1c5]/[0.08] text-[#8ee6dc]`;

  return (
    <table className="w-full text-[11px] border-collapse">
      <thead className="sticky top-0 z-10" style={{ backgroundColor: 'rgb(12, 20, 35)' }}>
        <tr className="text-[9.5px] uppercase tracking-wider">
          <th colSpan={7} className="px-2.5 pt-1.5 pb-1 text-left text-sky-300 font-semibold border-b border-sky-400/20">
            {t('table.group_incois')}
          </th>
          <th colSpan={oeCols} className="px-2.5 pt-1.5 pb-1 text-left text-[#4fd1c5] font-semibold bg-[#4fd1c5]/[0.08] border-b border-[#4fd1c5]/30">
            {t('table.group_oe')}
          </th>
          <th />
        </tr>
        <tr className="text-slate-400 border-b border-white/10">
          <th className={th}>{t('col.landmark')}</th>
          <th className={th}>{t('col.direction')}</th>
          <th className={th}>{t('col.bearing')}</th>
          <th className={th}>{t('col.distance', { unit: distUnitLabel(units.dist) })}</th>
          <th className={th}>{t('col.sea_depth', { unit: depthUnitLabel(units.depth) })}</th>
          <th className={th}>{t('col.lat')}</th>
          <th className={th}>{t('col.lon')}</th>
          <th className={thOe}>{t('col.d20')}</th>
          <th className={thOe}>{t('col.mld')}</th>
          <th className={thOe}>{t('col.front')}</th>
          {showGear && <th className={thOe}>{t('col.gear')}</th>}
          <th className={thOe}>{t('col.confidence')}</th>
          <th className={th}>{t('col.message')}</th>
        </tr>
      </thead>
      <tbody className="font-mono">
        {rows.map((r, i) => (
          <tr
            key={`${r.landmark}-${i}`}
            ref={(el) => {
              rowRefs.current[i] = el;
            }}
            onClick={() => onSelect(i)}
            className={`cursor-pointer border-b border-white/5 transition-colors ${
              selected === i ? 'bg-[#4fd1c5]/15' : 'hover:bg-white/[0.04]'
            }`}
          >
            <td className="px-2.5 py-1.5 font-sans text-slate-100 whitespace-nowrap">{r.landmark}</td>
            <td className="px-2.5 py-1.5 font-sans">{t(`direction.${r.direction}`)}</td>
            <td className="px-2.5 py-1.5">{r.bearing_deg ?? na}</td>
            <td className="px-2.5 py-1.5">{distRange(r, units.dist)}</td>
            <td className="px-2.5 py-1.5">{seaDepthRange(r, units.depth)}</td>
            <td className="px-2.5 py-1.5 whitespace-nowrap">{coordText(r, 'lat', units.coord)}</td>
            <td className="px-2.5 py-1.5 whitespace-nowrap">{coordText(r, 'lon', units.coord)}</td>
            <td className="px-2.5 py-1.5 bg-[#4fd1c5]/[0.04] text-white">{fmtDepth(r.d20_m, na)}</td>
            <td className="px-2.5 py-1.5 bg-[#4fd1c5]/[0.04] text-white">{fmtDepth(r.mld_m, na)}</td>
            <td className="px-2.5 py-1.5 bg-[#4fd1c5]/[0.04] font-sans">
              {r.subsurface_front === null ? na : r.subsurface_front ? <span className="text-pink-300">{t('yes')}</span> : t('no')}
            </td>
            {showGear && (
              <td className="px-2.5 py-1.5 bg-[#4fd1c5]/[0.04]">
                {r.gear_depth_from_m !== null ? `${Math.round(r.gear_depth_from_m)}–${Math.round(r.gear_depth_to_m ?? 0)}` : na}
              </td>
            )}
            <td className="px-2.5 py-1.5 bg-[#4fd1c5]/[0.04] font-sans whitespace-nowrap">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ background: CONFIDENCE_COLORS[r.confidence_level] }} />
                {t(`confidence.${r.confidence_level}`)}
              </span>
            </td>
            <td className="px-2.5 py-1">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onMessage(i);
                }}
                title={t('btn.message')}
                className="p-1.5 rounded-md text-slate-400 hover:text-[#4fd1c5] hover:bg-[#4fd1c5]/10"
              >
                <MessageSquare size={13} />
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
