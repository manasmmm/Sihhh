import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { PinnedPoint, ArgoFloat, MapLayer } from '../types';
import { getDerivedPngUrl } from '../api';
import { BasemapId, DEFAULT_BASEMAP, useBasemap } from '../basemaps';

interface MapViewProps {
  currentDate: string;
  currentDepth: number;
  pinnedPoints: PinnedPoint[];
  argoFloats: ArgoFloat[];
  showArgoFloats: boolean;
  adaptiveColor: boolean;
  onMapClick: (lat: number, lon: number) => void;
  onRemovePin: (id: string) => void;
  overlayOpacity: number;
  layer?: MapLayer;
  basemap?: BasemapId;
  /** Colour range the server used for the current temperature image (for the legend) */
  onRangeChange?: (vmin: number, vmax: number) => void;
}

export const MapView: React.FC<MapViewProps> = ({
  currentDate,
  currentDepth,
  pinnedPoints,
  argoFloats,
  showArgoFloats,
  adaptiveColor,
  onMapClick,
  onRemovePin,
  overlayOpacity,
  layer = 'thetao',
  basemap = DEFAULT_BASEMAP,
  onRangeChange,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<L.Map | null>(null);
  const imageOverlayRef = useRef<L.ImageOverlay | null>(null);
  const pinsLayerRef = useRef<L.LayerGroup | null>(null);
  const argoLayerRef = useRef<L.LayerGroup | null>(null);
  // Latest click handler (the Leaflet listener is registered once on init)
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;
  const onRangeChangeRef = useRef(onRangeChange);
  onRangeChangeRef.current = onRangeChange;
  const objectUrlRef = useRef<string | null>(null);

  // Exact North Indian Ocean Domain Bounding Box (Section 1)
  const domainBounds: L.LatLngBoundsLiteral = [
    [5.0, 45.0], // South-West [lat_min, lon_min]
    [30.0, 105.0], // North-East [lat_max, lon_max]
  ];

  // Pan constraint bounds (slightly larger for context)
  const maxPanBounds: L.LatLngBoundsLiteral = [
    [2.0, 40.0],
    [33.0, 110.0],
  ];

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || map) return;

    const mapInstance = L.map(mapContainerRef.current, {
      center: [16.5, 75.0],
      zoom: 5,
      minZoom: 4,
      maxZoom: 9,
      maxBounds: maxPanBounds,
      maxBoundsViscosity: 0.8,
      zoomControl: false,
    });

    // Custom Zoom control at top-right
    L.control.zoom({ position: 'topright' }).addTo(mapInstance);

    // Domain bounding box outline (elegant glowing cyan dashed frame)
    L.rectangle(domainBounds, {
      color: '#4fd1c5',
      weight: 1.5,
      dashArray: '8, 6',
      fill: false,
      opacity: 0.45,
      interactive: false,
    }).addTo(mapInstance);

    // Pins layer group
    const pinsLayer = L.layerGroup().addTo(mapInstance);
    pinsLayerRef.current = pinsLayer;

    // Argo float layer group
    const argoLayer = L.layerGroup().addTo(mapInstance);
    argoLayerRef.current = argoLayer;

    // Map click event listener
    mapInstance.on('click', (e: L.LeafletMouseEvent) => {
      onMapClickRef.current(e.latlng.lat, e.latlng.lng);
    });

    setMap(mapInstance);

    return () => {
      mapInstance.remove();
      setMap(null);
    };
  }, []);

  useBasemap(map, basemap);

  const showImage = (url: string) => {
    if (!map) return;
    if (!imageOverlayRef.current) {
      imageOverlayRef.current = L.imageOverlay(url, domainBounds, {
        opacity: overlayOpacity,
        interactive: false,
      }).addTo(map);
    } else {
      imageOverlayRef.current.setUrl(url);
    }
  };

  // Update the overlay image whenever the map, date, depth, contrast mode or layer changes.
  // Temperature images are fetched (not just linked) so the colour range the server
  // actually used (X-Vmin / X-Vmax headers) can be passed to the legend.
  useEffect(() => {
    if (!map) return;

    if (layer !== 'thetao') {
      showImage(getDerivedPngUrl(currentDate, layer));
      return;
    }

    const url = `/api/v1/field.png?date=${encodeURIComponent(currentDate)}&depth=${currentDepth}&scale=4&adaptive=${adaptiveColor}`;
    let cancelled = false; // a newer date/depth was requested before this one arrived
    fetch(url)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const vmin = parseFloat(res.headers.get('X-Vmin') ?? '');
        const vmax = parseFloat(res.headers.get('X-Vmax') ?? '');
        const blob = await res.blob();
        if (cancelled) return;
        const objectUrl = URL.createObjectURL(blob);
        const previous = objectUrlRef.current;
        objectUrlRef.current = objectUrl;
        showImage(objectUrl);
        if (previous) setTimeout(() => URL.revokeObjectURL(previous), 2000);
        if (isFinite(vmin) && isFinite(vmax)) onRangeChangeRef.current?.(vmin, vmax);
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('Failed to load temperature map:', err);
          showImage(url); // plain URL fallback; the legend keeps its last known range
        }
      });
    return () => {
      cancelled = true;
    };
  }, [map, currentDate, currentDepth, adaptiveColor, layer]);

  // Opacity changes only restyle the current image
  useEffect(() => {
    imageOverlayRef.current?.setOpacity(overlayOpacity);
  }, [overlayOpacity]);

  // Free the last image when the map goes away
  useEffect(
    () => () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    },
    []
  );

  // Update Pinned Points Markers
  useEffect(() => {
    const pinsLayer = pinsLayerRef.current;
    if (!pinsLayer) return;

    pinsLayer.clearLayers();

    pinnedPoints.forEach((pt) => {
      const pinIcon = L.divIcon({
        className: 'custom-leaflet-pin',
        html: `
          <div class="custom-pin" style="color: ${pt.color}; background-color: ${pt.color};">
            <div style="width: 8px; height: 8px; border-radius: 50%; background-color: #ffffff;"></div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([pt.snapped.lat, pt.snapped.lon], { icon: pinIcon });
      marker.bindTooltip(
        `<b>${pt.snapped.lat.toFixed(2)}°N, ${pt.snapped.lon.toFixed(2)}°E</b><br/>Click to remove`,
        { direction: 'top', offset: [0, -12], className: 'copernicus-tooltip' }
      );
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        onRemovePin(pt.id);
      });

      marker.addTo(pinsLayer);
    });
  }, [pinnedPoints, onRemovePin]);

  // Update Argo Floats Layer
  useEffect(() => {
    const argoLayer = argoLayerRef.current;
    if (!argoLayer) return;

    argoLayer.clearLayers();

    if (!showArgoFloats) return;

    argoFloats.forEach((f) => {
      const argoIcon = L.divIcon({
        className: 'argo-leaflet-pin',
        html: `<div class="argo-pin" title="Argo Float ${f.id}"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L.marker([f.lat, f.lon], { icon: argoIcon });
      marker.bindPopup(`
        <div style="color: #f1f5f9; font-family: 'Inter', sans-serif; font-size: 11px;">
          <div style="font-weight: bold; color: #38bdf8; margin-bottom: 2px;">Gridded Argo Float Profile</div>
          <div><b>WMO ID:</b> ${f.wmo}</div>
          <div><b>Region:</b> ${f.region}</div>
          <div><b>Coordinates:</b> ${f.lat}°N, ${f.lon}°E</div>
          <div><b>Last Obs:</b> ${f.last_profile}</div>
        </div>
      `);
      marker.addTo(argoLayer);
    });
  }, [argoFloats, showArgoFloats]);

  return <div ref={mapContainerRef} className="w-full h-full relative" />;
};
