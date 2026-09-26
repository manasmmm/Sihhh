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
  model_version?: string | null;
  per_date?: Record<string, { generated_at: string | null; valid_upto: string; model_version: string | null }>;
  front_threshold_c_per_km?: number;
  invalid_model_files?: ModelFileStatus[];
  /** model mode only: days already reconstructed by the in-backend GNN */
  ready_dates?: string[] | null;
}

export interface ModelFileStatus {
  file: string;
  date: string | null;
  format: string | null;
  valid: boolean;
  errors: string[];
  warnings: string[];
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
  valid_upto?: string;
  derived?: PointDerived;
  front_threshold_c_per_km?: number;
}

export interface PointDerived {
  d20: number | null;
  d26: number | null;
  mld: number | null;
  front_0m: number | null;
  front_50m: number | null;
  front_100m: number | null;
  subsurface_front_flag: boolean | null;
  tchp: number | null;
  confidence: number | null;
  confidence_level: ConfidenceLevel;
}

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'not_available';

export type DerivedVar =
  | 'd20'
  | 'd26'
  | 'mld'
  | 'front_0m'
  | 'front_50m'
  | 'front_100m'
  | 'subsurface_front_flag'
  | 'tchp'
  | 'confidence';

export type MapLayer = 'thetao' | DerivedVar;

export interface DerivedLegendInfo {
  var: DerivedVar;
  vmin: number;
  vmax: number;
  units: string;
  long_name: string;
  stops: string[];
  front_threshold_c_per_km: number;
  confidence_thresholds: { high: number; medium: number };
}

export interface ValidationMetric {
  depth_m: number;
  rmse_c: number | null;
  bias_c: number | null;
  corr: number | null;
  n: number | null;
}

export interface ValidationData {
  status: string;
  reference?: string;
  period?: string;
  message?: string;
  metrics: ValidationMetric[];
}

export interface PfzSector {
  code: string;
  name: string;
  bbox: [number, number, number, number];
  dates: string[];
}

export interface PfzRow {
  date: string;
  sector: string;
  landmark: string;
  direction: string;
  bearing_deg: number | null;
  dist_from_km: number | null;
  dist_to_km: number | null;
  sea_depth_from_m: number | null;
  sea_depth_to_m: number | null;
  lat_dms: string;
  lon_dms: string;
  lat: number;
  lon: number;
  valid_upto: string | null;
  d20_m: number | null;
  mld_m: number | null;
  front_50m: number | null;
  subsurface_front: boolean | null;
  confidence: number | null;
  confidence_level: ConfidenceLevel;
  gear_depth_from_m: number | null;
  gear_depth_to_m: number | null;
  profile: (number | null)[] | null;
  summary_text: string;
  grid_cell_lat: number | null;
  grid_cell_lon: number | null;
  note?: string;
}

export interface Species {
  name: string;
  t_min_c: number | null;
  t_max_c: number | null;
  source: string | null;
  configured: boolean;
}

export interface PfzEnriched {
  sector: string;
  sector_name: string;
  date: string;
  rows: PfzRow[];
  problems: string[];
  message: string | null;
  oceanembed_available: boolean;
  species: Species | null;
  source?: string;
  model_version?: string;
  confidence_note?: string;
  front_threshold_c_per_km: number;
}

export interface Language {
  code: string;
  name: string;
  status: string;
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
