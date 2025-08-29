'use client';

import { useMemo, useState } from 'react';
import L from 'leaflet';
import { Map as MapIcon, MapPin, Wifi, WifiOff, X } from 'lucide-react';
import { renderToString } from 'react-dom/server';
import {
  Circle,
  MapContainer,
  Marker,
  Rectangle,
  TileLayer,
  Tooltip,
  useMapEvents,
} from 'react-leaflet';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { Machine } from '@/lib/types/machine';
import { isValidCoordinate } from '@/lib/utils';

// Remove isMachineOnline import as it's deprecated

interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

const getMachineStatusColor = (
  machine: Machine,
  isSelected: boolean = false,
) => {
  if (isSelected) return 'bg-blue-500';

  // Use timestamp-based online detection (2 hours threshold)
  if (machine.last_location?.timestamp) {
    const lastSeen = new Date(machine.last_location.timestamp);
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
    if (lastSeen > twoHoursAgo) return 'bg-green-500';
  }
  return 'bg-gray-500';
};

const createMachineIcon = (machine: Machine, isSelected: boolean = false) => {
  const bgColor = getMachineStatusColor(machine, isSelected);

  const iconHtml = renderToString(
    <div className="relative">
      {/* Main marker */}
      <div
        className={`relative h-5 w-5 ${bgColor} flex items-center justify-center rounded-full border-2 border-white shadow-lg`}
      ></div>
    </div>,
  );

  return L.divIcon({
    html: iconHtml,
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    className: 'custom-machine-marker',
  });
};

// Rectangle Drawing Component
const RectangleDrawer = ({
  onBoundsSelected,
  existingBounds,
}: {
  onBoundsSelected: (bounds: MapBounds | null) => void;
  existingBounds: MapBounds | null;
}) => {
  const [drawing, setDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<L.LatLng | null>(null);
  const [currentBounds, setCurrentBounds] = useState<L.LatLngBounds | null>(
    existingBounds
      ? L.latLngBounds(
          [existingBounds.south, existingBounds.west],
          [existingBounds.north, existingBounds.east],
        )
      : null,
  );

  const map = useMapEvents({
    mousedown: (e) => {
      if (!drawing) {
        setDrawing(true);
        setStartPoint(e.latlng);
        setCurrentBounds(null);
        map.dragging.disable();
      }
    },
    mousemove: (e) => {
      if (drawing && startPoint) {
        const bounds = L.latLngBounds(startPoint, e.latlng);
        setCurrentBounds(bounds);
      }
    },
    mouseup: (e) => {
      if (drawing && startPoint) {
        const bounds = L.latLngBounds(startPoint, e.latlng);
        setCurrentBounds(bounds);
        setDrawing(false);
        setStartPoint(null);
        map.dragging.enable();

        // Convert to our bounds format
        const ne = bounds.getNorthEast();
        const sw = bounds.getSouthWest();
        onBoundsSelected({
          north: ne.lat,
          south: sw.lat,
          east: ne.lng,
          west: sw.lng,
        });
      }
    },
  });

  if (!currentBounds) return null;

  return (
    <Rectangle
      bounds={currentBounds}
      pathOptions={{
        color: '#3b82f6',
        weight: 2,
        opacity: 0.8,
        fillOpacity: 0.2,
        fillColor: '#3b82f6',
      }}
    />
  );
};

const MapFilter = ({
  machines,
  onAreaSelect,
  onClose,
  selectedBounds,
}: {
  machines: Machine[];
  onAreaSelect: (bounds: MapBounds | null) => void;
  onClose: () => void;
  selectedBounds: MapBounds | null;
}) => {
  const [tempBounds, setTempBounds] = useState<MapBounds | null>(
    selectedBounds,
  );

  // Calculate map center and zoom
  const getMapCenter = (): [number, number] => {

    const DEFAULT_LAT = 12.9205776; // VyomOS
    const DEFAULT_LNG = 77.6485081;
    
    if (!machines.length) return [DEFAULT_LAT, DEFAULT_LNG];

    // Get coordinates for each machine, using defaults for invalid ones
    const machineCoords = machines.map(machine => {
      const hasValidCoords = machine?.last_location?.lat && 
        machine?.last_location?.long &&
        isValidCoordinate(machine.last_location.lat, machine.last_location.long);
      
      return {
        lat: hasValidCoords ? machine.last_location.lat : DEFAULT_LAT,
        lng: hasValidCoords ? machine.last_location.long : DEFAULT_LNG
      };
    });

    const bounds = machineCoords.reduce(
      (acc, coords) => ({
        minLat: Math.min(acc.minLat, coords.lat),
        maxLat: Math.max(acc.maxLat, coords.lat),
        minLng: Math.min(acc.minLng, coords.lng),
        maxLng: Math.max(acc.maxLng, coords.lng),
      }),
      {
        minLat: machineCoords[0].lat,
        maxLat: machineCoords[0].lat,
        minLng: machineCoords[0].lng,
        maxLng: machineCoords[0].lng,
      },
    );

    return [
      (bounds.minLat + bounds.maxLat) / 2,
      (bounds.minLng + bounds.maxLng) / 2,
    ];
  };

  const getOptimalZoom = (): number => {
    if (machines.length <= 1) return 12;

    // Get coordinates for each machine, using defaults for invalid ones
    const machineCoords = machines.map(machine => {
      const hasValidCoords = machine?.last_location?.lat && 
        machine?.last_location?.long &&
        isValidCoordinate(machine.last_location.lat, machine.last_location.long);
      
      return {
        lat: hasValidCoords ? machine.last_location.lat : 12.9205776,
        lng: hasValidCoords ? machine.last_location.long : 77.6485081
      };
    });

    const bounds = machineCoords.reduce(
      (acc, coords) => ({
        minLat: Math.min(acc.minLat, coords.lat),
        maxLat: Math.max(acc.maxLat, coords.lat),
        minLng: Math.min(acc.minLng, coords.lng),
        maxLng: Math.max(acc.maxLng, coords.lng),
      }),
      {
        minLat: machineCoords[0].lat,
        maxLat: machineCoords[0].lat,
        minLng: machineCoords[0].lng,
        maxLng: machineCoords[0].lng,
      },
    );

    const latDiff = bounds.maxLat - bounds.minLat;
    const lngDiff = bounds.maxLng - bounds.minLng;
    const maxDiff = Math.max(latDiff, lngDiff);

    if (maxDiff > 1) return 8;
    if (maxDiff > 0.5) return 10;
    if (maxDiff > 0.1) return 12;
    return 14;
  };

  const handleApply = () => {
    onAreaSelect(tempBounds);
    onClose();
  };

  const handleClear = () => {
    setTempBounds(null);
    onAreaSelect(null);
  };

  const isMachineInBounds = (machine: Machine) => {
    if (!tempBounds) return false;
    if (!machine?.last_location) return false;

    // Check if coordinates are valid
    if (
      !isValidCoordinate(machine.last_location.lat, machine.last_location.long)
    ) {
      return false;
    }

    const inBounds =
      machine.last_location.lat >= tempBounds.south &&
      machine.last_location.lat <= tempBounds.north &&
      machine.last_location.long >= tempBounds.west &&
      machine.last_location.long <= tempBounds.east;

    return inBounds;
  };

  const selectedMachinesCount = tempBounds
    ? machines.filter((m) => isMachineInBounds(m)).length
    : 0;

  // Get machine status counts
  const machineStats = useMemo(() => {
    const selected = machines.filter((m) => isMachineInBounds(m));
    const all = tempBounds ? selected : machines;

    const online = all.filter(
      (m) => getMachineStatusColor(m) === 'bg-green-500',
    ).length;
    const offline = all.filter(
      (m) => getMachineStatusColor(m) === 'bg-gray-500',
    ).length;

    return { total: all.length, online, offline };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machines, tempBounds]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-h-[90vh] w-full max-w-4xl overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <MapIcon className="h-5 w-5" />
            Select Area Filter
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="overflow-auto">
          <div className="space-y-4">
            <div className="text-sm text-gray-600">
              Click and drag to select an area on the map. Only events from
              machines within the selected area will be shown in the calendar.
            </div>

            {/* Machine Statistics */}
            {tempBounds && (
              <div className="flex items-center gap-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-800">
                    Selected Area
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <Badge
                    variant="outline"
                    className="border-green-300 text-green-700"
                  >
                    <Wifi className="mr-1 h-3 w-3" />
                    {machineStats.online} Online
                  </Badge>
                  <Badge
                    variant="outline"
                    className="border-gray-300 text-gray-700"
                  >
                    <WifiOff className="mr-1 h-3 w-3" />
                    {machineStats.offline} Offline
                  </Badge>
                  <Badge variant="outline">{machineStats.total} Total</Badge>
                </div>
              </div>
            )}

            <div className="h-[500px] rounded-lg border bg-gray-50">
              <MapContainer
                center={getMapCenter()}
                zoom={getOptimalZoom()}
                style={{ height: '100%', width: '100%' }}
                className="rounded-lg"
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />

                <RectangleDrawer
                  onBoundsSelected={setTempBounds}
                  existingBounds={tempBounds}
                />

                {/* Machine markers */}
                {machines.map((machine) => (
                  <Marker
                    key={machine.id}
                    position={[
                      machine?.last_location?.lat ?? 12.9205776,
                      machine?.last_location?.long ?? 77.6485081,
                    ]}
                    icon={createMachineIcon(
                      machine,
                      isMachineInBounds(machine),
                    )}
                  >
                    <Tooltip>
                      <div className="text-center">
                        <div className="text-xs font-medium">
                          {machine.name}
                        </div>
                        <div className="text-xs text-gray-500">
                          ID: {machine.id}
                        </div>
                        <div className="text-xs text-gray-500">
                          Type: {machine.type.replace('_', ' ')}
                        </div>
                        <Badge
                          variant={
                            getMachineStatusColor(machine) === 'bg-green-500'
                              ? 'default'
                              : 'secondary'
                          }
                          className="mt-1 text-xs"
                        >
                          {getMachineStatusColor(machine) === 'bg-green-500'
                            ? 'Online'
                            : 'Offline'}
                        </Badge>
                      </div>
                    </Tooltip>
                  </Marker>
                ))}

                {/* Coverage circles for selected machines */}
                {machines
                  .filter((m) => isMachineInBounds(m))
                  .map((machine) => (
                    <Circle
                      key={`coverage-${machine.id}`}
                      center={[
                        machine?.last_location?.lat ?? 12.9205776,
                        machine?.last_location?.long ?? 77.6485081,
                      ]}
                      radius={200}
                      pathOptions={{
                        color: '#3b82f6',
                        weight: 1,
                        opacity: 0.4,
                        fillOpacity: 0.1,
                        fillColor: '#3b82f6',
                      }}
                    />
                  ))}
              </MapContainer>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {tempBounds
                  ? `${selectedMachinesCount} machine${selectedMachinesCount !== 1 ? 's' : ''} selected`
                  : 'Click and drag to select an area'}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={handleClear}>
                  Clear Selection
                </Button>
                <Button onClick={handleApply}>Apply Filter</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MapFilter;
