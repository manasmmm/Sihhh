import {
  Metadata,
  ProfileResponse,
  TimeseriesResponse,
  ArgoFloat,
  BasinAverageData,
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

export async function inferDate(date: string): Promise<any> {
  const res = await fetch(`${API_BASE}/infer?date=${encodeURIComponent(date)}`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Inference failed: ${res.statusText}`);
  }
  return res.json();
}
