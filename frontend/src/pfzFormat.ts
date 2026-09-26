import { PfzRow } from './types';
import { KM_PER_NM, M_PER_FATHOM, prettyDms } from './i18n';

export type DistUnit = 'km' | 'nm';
export type DepthUnit = 'm' | 'fathom';
export type CoordFmt = 'dms' | 'decimal';

export interface Units {
  dist: DistUnit;
  depth: DepthUnit;
  coord: CoordFmt;
}

const round = (v: number, nd: number) => {
  const f = Math.pow(10, nd);
  return Math.round(v * f) / f;
};

export function distValue(km: number | null, unit: DistUnit): string {
  if (km === null || km === undefined) return '—';
  return unit === 'km' ? String(round(km, 1)) : String(round(km / KM_PER_NM, 1));
}

export function seaDepthValue(m: number | null, unit: DepthUnit): string {
  if (m === null || m === undefined) return '—';
  return unit === 'm' ? String(round(m, 1)) : String(round(m / M_PER_FATHOM, 1));
}

export const distRange = (r: PfzRow, u: DistUnit) => `${distValue(r.dist_from_km, u)}–${distValue(r.dist_to_km, u)}`;
export const seaDepthRange = (r: PfzRow, u: DepthUnit) =>
  `${seaDepthValue(r.sea_depth_from_m, u)}–${seaDepthValue(r.sea_depth_to_m, u)}`;

export function coordText(r: PfzRow, which: 'lat' | 'lon', fmt: CoordFmt): string {
  const v = which === 'lat' ? r.lat : r.lon;
  if (fmt === 'decimal') return `${v.toFixed(4)}°${which === 'lat' ? (v >= 0 ? 'N' : 'S') : v >= 0 ? 'E' : 'W'}`;
  return prettyDms(which === 'lat' ? r.lat_dms : r.lon_dms, v, which === 'lat');
}

export const distUnitLabel = (u: DistUnit) => (u === 'km' ? 'km' : 'nm');
export const depthUnitLabel = (u: DepthUnit) => (u === 'm' ? 'm' : 'fathoms');

export const depthText = (v: number | null) => (v === null || v === undefined ? null : `${Math.round(v)} m`);
