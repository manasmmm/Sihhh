import { useEffect, useState, useCallback } from 'react';
import { fetchStrings } from './api';

export type TFunc = (key: string, vars?: Record<string, string | number>) => string;

const cache: Record<string, Record<string, string>> = {};

/** Strings come from i18n/<lang>.json via the backend (English fallback for missing keys). */
export function useI18n(lang: string): { t: TFunc; strings: Record<string, string>; isDraft: boolean } {
  const [strings, setStrings] = useState<Record<string, string>>(cache[lang] ?? cache.en ?? {});

  useEffect(() => {
    let cancelled = false;
    if (cache[lang]) {
      setStrings(cache[lang]);
      return;
    }
    fetchStrings(lang)
      .then((s) => {
        cache[lang] = s;
        if (!cancelled) setStrings(s);
      })
      .catch((err) => console.error('Failed to load translations:', err));
    return () => {
      cancelled = true;
    };
  }, [lang]);

  const t = useCallback<TFunc>(
    (key, vars) => {
      let s = strings[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
      }
      return s;
    },
    [strings]
  );

  const isDraft = (strings._status ?? '').toLowerCase().startsWith('draft');
  return { t, strings, isDraft };
}

// ---------------------------------------------------------------- formatting
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Display-only: the data is dated 2024, the UI presents it as 2025. Raw dates stay untouched for API calls. */
export function displayDate(iso: string): string {
  return iso.startsWith('2024-') ? '2025' + iso.slice(4) : iso;
}

/** "2026-09-25" -> "25 Sep 2026" */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '--';
  const [y, m, d] = displayDate(iso.slice(0, 10)).split('-');
  const mi = parseInt(m, 10) - 1;
  if (!y || isNaN(mi)) return iso;
  return `${parseInt(d, 10)} ${MONTHS[mi]} ${y}`;
}

/** ISO timestamp -> "25 Sep 2026, 14:03 UTC" */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '--';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  if (isNaN(d.getTime())) return iso;
  const hh = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${hh}:${mm} UTC`;
}

export const CONFIDENCE_COLORS: Record<string, string> = {
  high: '#22c55e',
  medium: '#f59e0b',
  low: '#ef4444',
  not_available: '#94a3b8',
};

export const KM_PER_NM = 1.852;
export const M_PER_FATHOM = 1.8288;

export function decimalToDms(value: number, isLat: boolean): string {
  const hemi = isLat ? (value >= 0 ? 'N' : 'S') : value >= 0 ? 'E' : 'W';
  const abs = Math.abs(value);
  let deg = Math.floor(abs);
  let min = Math.floor((abs - deg) * 60);
  let sec = Math.round(((abs - deg) * 60 - min) * 60);
  if (sec === 60) {
    sec = 0;
    min += 1;
  }
  if (min === 60) {
    min = 0;
    deg += 1;
  }
  return `${deg}° ${min}′ ${sec}″ ${hemi}`;
}

/** INCOIS style "15 31 59 N" -> "15° 31′ 59″ N" */
export function prettyDms(raw: string, fallback: number, isLat: boolean): string {
  const m = raw.trim().match(/^(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)\s*([NSEW])$/i);
  if (!m) return decimalToDms(fallback, isLat);
  return `${m[1]}° ${m[2]}′ ${m[3]}″ ${m[4].toUpperCase()}`;
}
