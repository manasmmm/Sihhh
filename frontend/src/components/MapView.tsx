import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { PinnedPoint, ArgoFloat, MapLayer } from '../types';
import { getDerivedPngUrl, getFieldImageUrl } from '../api';
import { loadImage, nearestFirst, pinImage, prefetchImages } from '../imageCache';
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
  /** All dates on the time slider (for preloading) */
  dates?: string[];
  /** Changes when the model output changes (cache-busting for images) */
  dataVersion?: string;
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
  dates = [],
  dataVersion = '',
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

  const imageUrlFor = (date: string) =>
    layer === 'thetao'
      ? getFieldImageUrl(date, currentDepth, adaptiveColor, dataVersion)
      : getDerivedPngUrl(date, layer, 4, dataVersion);

  // Show the image for the current date/depth/layer from the in-memory cache (downloading
  // it if needed), pass the server's colour range to the legend, then preload the other
  // days so moving the time slider is instant.
  useEffect(() => {
    if (!map) return;
    const url = imageUrlFor(currentDate);
    let cancelled = false; // a newer date/depth was requested before this one arrived
    loadImage(url)
      .then((img) => {
        if (cancelled) return;
        pinImage(url);
        showImage(img.url);
        if (layer === 'thetao' && img.vmin !== null && img.vmax !== null) {
          onRangeChangeRef.current?.(img.vmin, img.vmax);
        }
        prefetchImages(nearestFirst(dates, currentDate).map(imageUrlFor));
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('Failed to load map image:', err);
          showImage(url); // plain URL fallback; the legend keeps its last known range
        }
      });
    return () => {
      cancelled = true;
    };
  }, [map, currentDate, currentDepth, adaptiveColor, layer, dataVersion, dates]);

  // Opacity changes only restyle the current image
  useEffect(() => {
    imageOverlayRef.current?.setOpacity(overlayOpacity);
  }, [overlayOpacity]);

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
