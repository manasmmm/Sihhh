import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { PinnedPoint, ArgoFloat } from '../types';

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
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<L.Map | null>(null);
  const imageOverlayRef = useRef<L.ImageOverlay | null>(null);
  const pinsLayerRef = useRef<L.LayerGroup | null>(null);
  const argoLayerRef = useRef<L.LayerGroup | null>(null);

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

    // Esri Dark Gray Canvas basemap (key-free) + reference layer for city/place labels
    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: '&copy; <a href="https://www.esri.com/">Esri</a>',
        maxZoom: 16,
      }
    ).addTo(mapInstance);

    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: '&copy; <a href="https://www.esri.com/">Esri</a>',
        maxZoom: 16,
        pane: 'shadowPane',
      }
    ).addTo(mapInstance);

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
      onMapClick(e.latlng.lat, e.latlng.lng);
    });

    setMap(mapInstance);

    return () => {
      mapInstance.remove();
      setMap(null);
    };
  }, []);

  // Update ImageOverlay whenever map, date, depth, opacity, or adaptive contrast changes
  useEffect(() => {
    if (!map) return;

    const imgUrl = `/api/v1/field.png?date=${encodeURIComponent(currentDate)}&depth=${currentDepth}&scale=4&adaptive=${adaptiveColor}`;

    if (!imageOverlayRef.current) {
      // First creation
      const overlay = L.imageOverlay(imgUrl, domainBounds, {
        opacity: overlayOpacity,
        interactive: false,
      }).addTo(map);
      imageOverlayRef.current = overlay;
    } else {
      // Update image URL and opacity seamlessly
      imageOverlayRef.current.setUrl(imgUrl);
      imageOverlayRef.current.setOpacity(overlayOpacity);
    }
  }, [map, currentDate, currentDepth, overlayOpacity, adaptiveColor]);

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
