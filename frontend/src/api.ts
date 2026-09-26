import {
  Metadata,
  ProfileResponse,
  TimeseriesResponse,
  ArgoFloat,
  BasinAverageData,
  DerivedLegendInfo,
  DerivedVar,
  Language,
  ModelFileStatus,
  PfzEnriched,
  PfzSector,
  Species,
  ValidationData,
} from './types';

const API_BASE = '/api/v1';

export async function fetchMetadata(): Promise<Metadata> {
  const res = await fetch(`${API_BASE}/metadata`);
  if (!res.ok) {
    throw new Error(`Failed to fetch metadata: ${res.statusText}`);
  }
  return res.json();
}

export function getFieldPngUrl(date: string, depth: number, scale: number = 4): string {
  return `${API_BASE}/field.png?date=${encodeURIComponent(date)}&depth=${depth}&scale=${scale}`;
}

export async function fetchProfile(
  lat: number,
  lon: number,
  date: string
): Promise<ProfileResponse> {
  const res = await fetch(
    `${API_BASE}/profile?lat=${lat}&lon=${lon}&date=${encodeURIComponent(date)}`
  );
  if (res.status === 422) {
    const errorJson = await res.json();
    throw { isLandCell: true, snapped: errorJson.snapped };
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch profile: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTimeseries(
  lat: number,
  lon: number,
  depth: number
): Promise<TimeseriesResponse> {
  const res = await fetch(
    `${API_BASE}/timeseries?lat=${lat}&lon=${lon}&depth=${depth}`
  );
  if (res.status === 422) {
    const errorJson = await res.json();
    throw { isLandCell: true, snapped: errorJson.snapped };
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch timeseries: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchBasinAverage(depth: number): Promise<BasinAverageData> {
  const res = await fetch(`${API_BASE}/basin_average?depth=${depth}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch basin average: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchArgoFloats(): Promise<{ count: number; floats: ArgoFloat[] }> {
  const res = await fetch(`${API_BASE}/argo_floats`);
  if (!res.ok) {
    throw new Error(`Failed to fetch Argo floats: ${res.statusText}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Additions: derived layers, PFZ, validation, exports, i18n, model output
// ---------------------------------------------------------------------------
async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      if (j && j.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.json();
}

/** Metadata, with the backend's message (e.g. "model not implemented yet") on failure. */
export function fetchMeta(): Promise<Metadata> {
  return getJson<Metadata>(`${API_BASE}/meta`);
}

export function getDerivedPngUrl(date: string, variable: DerivedVar, scale: number = 4): string {
  return `${API_BASE}/derived.png?date=${encodeURIComponent(date)}&var=${variable}&scale=${scale}`;
}

const legendCache: Partial<Record<DerivedVar, Promise<DerivedLegendInfo>>> = {};
export function fetchDerivedLegend(variable: DerivedVar): Promise<DerivedLegendInfo> {
  let p = legendCache[variable];
  if (!p) {
    p = getJson<DerivedLegendInfo>(`${API_BASE}/derived/legend?var=${variable}`);
    p.catch(() => delete legendCache[variable]);
    legendCache[variable] = p;
  }
  return p;
}

export function fetchValidation(): Promise<ValidationData> {
  return getJson<ValidationData>(`${API_BASE}/validation`);
}

export function fetchPfzSectors(): Promise<{ default: string; bbox_note: string; sectors: PfzSector[] }> {
  return getJson(`${API_BASE}/pfz/sectors`);
}

export function fetchPfzEnriched(
  sector: string,
  date: string,
  species: string | null,
  lang: string
): Promise<PfzEnriched> {
  const sp = species ? `&species=${encodeURIComponent(species)}` : '';
  return getJson<PfzEnriched>(
    `${API_BASE}/pfz/enriched?sector=${encodeURIComponent(sector)}&date=${encodeURIComponent(date)}&lang=${lang}${sp}`
  );
}

export function pfzCsvUrl(sector: string, date: string, species: string | null, lang: string): string {
  const sp = species ? `&species=${encodeURIComponent(species)}` : '';
  return `${API_BASE}/export/pfz.csv?sector=${encodeURIComponent(sector)}&date=${encodeURIComponent(date)}&lang=${lang}${sp}`;
}

export function fetchSpecies(): Promise<{ species: Species[]; any_configured: boolean; message: string | null }> {
  return getJson(`${API_BASE}/species`);
}

export function fetchLanguages(): Promise<{ default: string; languages: Language[] }> {
  return getJson(`${API_BASE}/i18n`);
}

export function fetchStrings(lang: string): Promise<Record<string, string>> {
  return getJson(`${API_BASE}/i18n/${lang}`);
}

export function fetchModelOutputStatus(): Promise<{ folder: string; active: boolean; files: ModelFileStatus[] }> {
  return getJson(`${API_BASE}/model-output/status`);
}

export const netcdfUrl = (date: string) => `${API_BASE}/export/netcdf?date=${encodeURIComponent(date)}`;
export const derivedNetcdfUrl = (date: string) => `${API_BASE}/export/derived?date=${encodeURIComponent(date)}`;

/** Download through fetch so a backend error is shown instead of a raw JSON page. */
export async function downloadFile(url: string, filename: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

export interface UploadResult {
  saved: boolean;
  errors: string[];
  warnings: string[];
  date: string | null;
}

export async function uploadModelOutput(file: File, modelVersion?: string): Promise<UploadResult> {
  const mv = modelVersion ? `&model_version=${encodeURIComponent(modelVersion)}` : '';
  const res = await fetch(`${API_BASE}/model-output/upload?filename=${encodeURIComponent(file.name)}${mv}`, {
    method: 'POST',
    body: file,
    headers: { 'Content-Type': 'application/octet-stream' },
  });
  const j = await res.json().catch(() => ({}));
  if (res.status === 422 && Array.isArray(j.errors)) {
    return { saved: false, errors: j.errors, warnings: j.warnings ?? [], date: j.date ?? null };
  }
  if (!res.ok) throw new Error(typeof j.detail === 'string' ? j.detail : res.statusText);
  return j;
}

export async function inferDate(date: string): Promise<any> {
  const res = await fetch(`${API_BASE}/infer?date=${encodeURIComponent(date)}`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Inference failed: ${res.statusText}`);
  }
  return res.json();
}
