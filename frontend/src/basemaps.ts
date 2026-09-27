import { useEffect } from 'react';
import L from 'leaflet';

/**
 * Background maps. All are free, need no API key and were checked for watermarks
 * (CARTO's basemaps now require a key, so they are not offered).
 * Labels are drawn in their own pane ABOVE the temperature overlay, so place
 * names and coastlines stay visible on top of the data.
 */
export type BasemapId = 'satellite' | 'bluemarble' | 'blackmarble' | 'ocean' | 'dark-gray';

interface TileDef {
  url: string;
  maxNativeZoom?: number;
  subdomains?: string;
}

interface BasemapDef {
  id: BasemapId;
  label: string;
  base: TileDef;
  labels?: TileDef;
  attribution: string;
}

const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services';
const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best';
const ESRI_ATTR = '&copy; <a href="https://www.esri.com/">Esri</a>';
const NASA_ATTR = 'Imagery &copy; <a href="https://earthdata.nasa.gov/gibs">NASA GIBS</a>';
const ESRI_PLACES: TileDef = { url: `${ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}` };

export const BASEMAPS: BasemapDef[] = [
  {
    id: 'satellite',
    label: 'Satellite (Sentinel-2)',
    base: { url: 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg' },
    labels: ESRI_PLACES,
    attribution:
      '<a href="https://s2maps.eu">Sentinel-2 cloudless</a> by <a href="https://eox.at">EOX IT Services GmbH</a> ' +
      '(contains modified Copernicus Sentinel data 2020), ' + ESRI_ATTR,
  },
  {
    id: 'bluemarble',
    label: 'NASA Blue Marble + sea floor',
    base: { url: `${GIBS}/BlueMarble_ShadedRelief_Bathymetry/default/2004-08-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`, maxNativeZoom: 8 },
    labels: ESRI_PLACES,
    attribution: `${NASA_ATTR}, ${ESRI_ATTR}`,
  },
  {
    id: 'blackmarble',
    label: 'NASA Black Marble (night)',
    base: { url: `${GIBS}/VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`, maxNativeZoom: 8 },
    labels: ESRI_PLACES,
    attribution: `${NASA_ATTR}, ${ESRI_ATTR}`,
  },
  {
    id: 'ocean',
    label: 'Ocean bathymetry (light)',
    base: { url: `${ESRI}/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}`, maxNativeZoom: 10 },
    labels: { url: `${ESRI}/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}`, maxNativeZoom: 10 },
    attribution: `${ESRI_ATTR}, GEBCO, NOAA, National Geographic`,
  },
  {
    id: 'dark-gray',
    label: 'Dark gray (original)',
    base: { url: `${ESRI}/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`, maxNativeZoom: 16 },
    labels: { url: `${ESRI}/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}`, maxNativeZoom: 16 },
    attribution: ESRI_ATTR,
  },
];

export const DEFAULT_BASEMAP: BasemapId = 'satellite';
const STORAGE_KEY = 'oceanembed.basemap.v2';

export function loadBasemapChoice(): BasemapId {
  try {
    const v = localStorage.getItem(STORAGE_KEY) as BasemapId | null;
    if (v && BASEMAPS.some((b) => b.id === v)) return v;
  } catch {
    /* storage unavailable */
  }
  return DEFAULT_BASEMAP;
}

export function saveBasemapChoice(id: BasemapId) {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* storage unavailable */
  }
}

const LABEL_PANE = 'basemapLabels';

function tile(def: TileDef, attribution: string, pane?: string): L.TileLayer {
  const opts: L.TileLayerOptions = {
    attribution,
    subdomains: def.subdomains ?? 'abc',
    maxNativeZoom: def.maxNativeZoom ?? 18,
    maxZoom: 18,
  };
  if (pane) opts.pane = pane; // an explicit `pane: undefined` would override Leaflet's default tile pane
  return L.tileLayer(def.url, opts);
}

/** Keeps the map's background tiles in sync with the chosen basemap. */
export function useBasemap(map: L.Map | null, id: BasemapId) {
  useEffect(() => {
    if (!map) return;
    if (!map.getPane(LABEL_PANE)) {
      const pane = map.createPane(LABEL_PANE);
      pane.style.zIndex = '450'; // above the temperature overlay (400), below markers (600)
      pane.style.pointerEvents = 'none';
    }
    const def = BASEMAPS.find((b) => b.id === id) ?? BASEMAPS[0];
    const layers = [tile(def.base, def.attribution)];
    if (def.labels) layers.push(tile(def.labels, '', LABEL_PANE));
    layers.forEach((l) => l.addTo(map));
    layers[0].bringToBack();
    return () => {
      layers.forEach((l) => l.remove());
    };
  }, [map, id]);
}
