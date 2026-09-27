import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { DerivedVar, PfzRow } from '../types';
import { getDerivedPngUrl } from '../api';
import { CONFIDENCE_COLORS } from '../i18n';
import { BasemapId, DEFAULT_BASEMAP, useBasemap } from '../basemaps';

interface FisheriesMapProps {
  date: string | null;
  layer: DerivedVar | 'none';
  bbox: [number, number, number, number] | null; // [lat_min, lon_min, lat_max, lon_max]
  rows: PfzRow[];
  selected: number | null;
  onSelect: (idx: number) => void;
  opacity?: number;
  basemap?: BasemapId;
}

const DOMAIN: L.LatLngBoundsLiteral = [
  [5.0, 45.0],
  [30.0, 105.0],
];

export const FisheriesMap: React.FC<FisheriesMapProps> = ({
  date,
  layer,
  bbox,
  rows,
  selected,
  onSelect,
  opacity = 0.75,
  basemap = DEFAULT_BASEMAP,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<L.Map | null>(null);
  const overlayRef = useRef<L.ImageOverlay | null>(null);
  const markersRef = useRef<L.LayerGroup | null>(null);
  const markerList = useRef<L.CircleMarker[]>([]);
  const bboxRef = useRef<L.Rectangle | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!containerRef.current || map) return;
    const m = L.map(containerRef.current, {
      center: [15.3, 73.5],
      zoom: 8,
      minZoom: 4,
      maxZoom: 12,
      maxBounds: [
        [2.0, 40.0],
        [33.0, 110.0],
      ],
      maxBoundsViscosity: 0.8,
      zoomControl: false,
    });
    L.control.zoom({ position: 'topleft' }).addTo(m);
    markersRef.current = L.layerGroup().addTo(m);
    setMap(m);
    // Keep Leaflet in sync when the table panel below is resized
    const ro = new ResizeObserver(() => m.invalidateSize());
    ro.observe(containerRef.current);
    return () => {
      ro.disconnect();
      m.remove();
      setMap(null);
    };
  }, []);

  useBasemap(map, basemap);

  // Background derived layer
  useEffect(() => {
    if (!map) return;
    if (!date || layer === 'none') {
      overlayRef.current?.remove();
      overlayRef.current = null;
      return;
    }
    const url = getDerivedPngUrl(date, layer);
    if (!overlayRef.current) {
      overlayRef.current = L.imageOverlay(url, DOMAIN, { opacity, interactive: false }).addTo(map);
    } else {
      overlayRef.current.setUrl(url);
      overlayRef.current.setOpacity(opacity);
    }
  }, [map, date, layer, opacity]);

  // Sector outline + zoom
  useEffect(() => {
    if (!map || !bbox) return;
    const b: L.LatLngBoundsLiteral = [
      [bbox[0], bbox[1]],
      [bbox[2], bbox[3]],
    ];
    bboxRef.current?.remove();
    bboxRef.current = L.rectangle(b, { color: '#4fd1c5', weight: 1, dashArray: '4 4', fill: false, opacity: 0.6, interactive: false }).addTo(map);
    map.fitBounds(b, { padding: [30, 30] });
  }, [map, bbox]);

  // PFZ markers
  useEffect(() => {
    const group = markersRef.current;
    if (!map || !group) return;
    group.clearLayers();
    markerList.current = rows.map((r, i) => {
      const mk = L.circleMarker([r.lat, r.lon], {
        radius: 8,
        color: '#ffffff',
        weight: 1.5,
        fillColor: CONFIDENCE_COLORS[r.confidence_level] ?? CONFIDENCE_COLORS.not_available,
        fillOpacity: 0.95,
      });
      mk.bindTooltip(r.landmark, { direction: 'top', offset: [0, -8], className: 'copernicus-tooltip' });
      mk.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        onSelectRef.current(i);
      });
      mk.addTo(group);
      return mk;
    });
  }, [map, rows]);

  // Highlight + pan to the selected marker
  useEffect(() => {
    if (!map) return;
    markerList.current.forEach((mk, i) => {
      const sel = i === selected;
      mk.setStyle({ radius: sel ? 12 : 8, weight: sel ? 3 : 1.5, color: sel ? '#4fd1c5' : '#ffffff' });
      if (sel) mk.bringToFront();
    });
    if (selected !== null && rows[selected]) {
      map.panTo([rows[selected].lat, rows[selected].lon], { animate: true });
    }
  }, [map, selected, rows]);

  return <div ref={containerRef} className="w-full h-full relative" />;
};
