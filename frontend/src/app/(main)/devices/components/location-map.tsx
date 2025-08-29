'use client';

import React from 'react';
import { MapContainer, Marker, TileLayer } from 'react-leaflet';
import L from 'leaflet';

import 'leaflet/dist/leaflet.css';

interface LocationMapProps {
  lat: number;
  long: number;
  className?: string;
}

// Fix for default marker icons in React Leaflet
delete (L.Icon.Default.prototype as unknown as { _getIconUrl: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const LocationMap: React.FC<LocationMapProps> = ({ lat, long, className = '' }) => {
  const defaultLat = 12.9205724;
  const defaultLong = 77.651083;
  
  // Helper function to safely validate and convert coordinates
  const getValidCoordinate = (coord: number | undefined | null, isLongitude: boolean = false): number => {
    try {
      // Convert to number if it's a string or other type
      const numCoord = Number(coord);
      
      // Check if it's a valid finite number and not zero
      if (typeof numCoord === 'number' && !isNaN(numCoord) && isFinite(numCoord) && numCoord !== 0) {
        return numCoord;
      }
      
      // Return appropriate default based on coordinate type
      return isLongitude ? defaultLong : defaultLat;
    } catch (error) {
      console.warn('Invalid coordinate value:', coord, error);
      return isLongitude ? defaultLong : defaultLat;
    }
  };
  
  // Use provided coordinates or fall back to defaults
  const displayLat = getValidCoordinate(lat, false);
  const displayLong = getValidCoordinate(long, true);

  // Create custom marker with coordinates text
  const createCustomMarker = () => {
    const coordinatesText = `${Number(displayLat).toFixed(2)}, ${Number(displayLong).toFixed(2)}`;
    
    // Create a custom HTML element for the marker
    const markerHtml = `
      <div style="
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        transform: translate(-50%, -100%);
      ">
        <div style="
          background: white;
          color: #333;
          font-family: monospace;
          font-size: 10px;
          padding: 2px 4px;
          border-radius: 3px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.3);
          white-space: nowrap;
          margin-bottom: 5px;
          z-index: 1000;
        ">
          ${coordinatesText}
        </div>
        <div style="
          width: 0;
          height: 0;
          border-left: 6px solid transparent;
          border-right: 6px solid transparent;
          border-top: 6px solid white;
          margin-bottom: 2px;
        "></div>
        <div style="
          width: 12px;
          height: 12px;
          background: #e74c3c;
          border: 2px solid white;
          border-radius: 50%;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        "></div>
      </div>
    `;

    return L.divIcon({
      html: markerHtml,
      className: 'custom-marker',
      iconSize: [120, 60],
      iconAnchor: [0, -10]
    });
  };

  return (
    <div className={`relative ${className}`}>
      <MapContainer
        center={[displayLat, displayLong]}
        zoom={13}
        style={{ height: '120px', width: '160px' }}
        zoomControl={false}
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        touchZoom={false}
        className="rounded-md border"
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />
        <Marker 
          position={[displayLat, displayLong]} 
          icon={createCustomMarker()}
        />
      </MapContainer>
    </div>
  );
};

export default LocationMap;
