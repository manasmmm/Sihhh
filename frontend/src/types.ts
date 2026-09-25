export interface DomainInfo {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
  resolution_deg: number;
}

export interface GridShape {
  lat: number;
  lon: number;
}

export interface DatesInfo {
  start: string;
  end: string;
  count: number;
  all_dates: string[];
}

export interface VariableInfo {
  name: string;
  long_name: string;
  units: string;
  colorbar_range: [number, number];
}

export interface ModelInfo {
  architecture: string;
  resolution: string;
  region: string;
}

export interface Metadata {
  domain: DomainInfo;
  grid_shape: GridShape;
  depths_m: number[];
  dates: DatesInfo;
  variable: VariableInfo;
  model_info?: ModelInfo;
  data_source?: string;
  model_version?: string;
}

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface ProfileStats {
  min: number | null;
  max: number | null;
}

export interface ProfileResponse {
  requested: Coordinates;
  snapped: Coordinates;
  date: string;
  depths_m: number[];
  temperature_c: (number | null)[];
  stats: ProfileStats;
  error?: string;
}

export interface TimeseriesStats {
  min: number | null;
  median: number | null;
  max: number | null;
}

export interface TimeseriesResponse {
  requested: Coordinates;
  snapped: Coordinates;
  depth: number;
  dates: string[];
  temperature_c: (number | null)[];
  stats: TimeseriesStats;
  error?: string;
}

export interface PinnedPoint {
  id: string;
  color: string;
  snapped: Coordinates;
  requested: Coordinates;
  profile?: ProfileResponse;
  timeseries?: TimeseriesResponse;
  loadingProfile: boolean;
  loadingTimeseries: boolean;
  error?: string;
}

export interface ArgoFloat {
  id: string;
  lat: number;
  lon: number;
  region: string;
  last_profile: string;
  wmo: number;
}

export interface BasinAverageData {
  depth: number;
  dates: string[];
  temperature_c: number[];
  stats: TimeseriesStats;
}
