import { useMemo, useState } from 'react';
import L from 'leaflet';
import {
  Activity,
  AlertTriangle,
  Eye,
  Map as MapIcon,
  MapPin,
  Shield,
  X,
} from 'lucide-react';
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

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { Machine, MachineData } from '@/lib/types/machine';
import { useLiveMachineData } from '@/hooks/use-live-machine-data';

interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

// Get machine type icon (matching your existing implementation)
const getMachineTypeIcon = (type: string, size: number = 16) => {
  switch (type) {
    case 'perimeter_guard':
      return <Shield size={size} className="text-white" />;
    case 'mobile_patrol':
      return <Activity size={size} className="text-white" />;
    case 'fixed_surveillance':
      return <Eye size={size} className="text-white" />;
    case 'roving_sensor':
      return <AlertTriangle size={size} className="text-white" />;
    default:
      return <MapPin size={size} className="text-white" />;
  }
};

// Create custom marker icon
const createMachineIcon = (machine: Machine, machineData: MachineData, isSelected: boolean = false) => {
  if (!machineData) return undefined;

  const bgColor = isSelected
    ? 'bg-blue-500'
    : machineData?.status === 'offline'
      ? 'bg-gray-500'
      : machineData?.status === 'maintenance'
        ? 'bg-yellow-500'
        : 'bg-green-500';

  const iconHtml = renderToString(
    <div className="relative">
      <div
        className={`relative h-10 w-10 ${bgColor} flex items-center justify-center rounded-full border-2 border-white shadow-lg`}
      >
        <MapPin size={20} className="text-white" />
      </div>
      <div className="absolute -top-1 -left-1 flex h-4 w-4 items-center justify-center rounded-full border border-white bg-blue-500">
        {getMachineTypeIcon(machine.type, 8)}
      </div>
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

  // Get machine IDs for the hook
  const machineIds = useMemo(() => machines.map((m) => m.id), [machines]);

  // Use the live data hook
  const { getMachineData } =
    useLiveMachineData(machineIds, true);

  // Calculate map center and zoom
  const getMapCenter = (): [number, number] => {
    if (!machines.length) return [12.9716, 77.5946]; // Default to Bangalore

    const bounds = machines.reduce(
      (acc, m) => ({
        minLat: Math.min(acc.minLat, m.last_location.lat),
        maxLat: Math.max(acc.maxLat, m.last_location.lat),
        minLng: Math.min(acc.minLng, m.last_location.lng),
        maxLng: Math.max(acc.maxLng, m.last_location.lng),
      }),
      {
        minLat: machines[0]?.last_location?.lat ?? 0,
        maxLat: machines[0]?.last_location?.lat ?? 0,
        minLng: machines[0]?.last_location?.lng ?? 0,
        maxLng: machines[0]?.last_location?.lng ?? 0,
      },
    );

    return [
      (bounds.minLat + bounds.maxLat) / 2,
      (bounds.minLng + bounds.maxLng) / 2,
    ];
  };

  const getOptimalZoom = (): number => {
    if (machines.length <= 1) return 12;

    const bounds = machines.reduce(
      (acc, m) => ({
        minLat: Math.min(acc.minLat, m.last_location.lat),
        maxLat: Math.max(acc.maxLat, m.last_location.lat),
        minLng: Math.min(acc.minLng, m.last_location.lng),
        maxLng: Math.max(acc.maxLng, m.last_location.lng),
      }),
      {
        minLat: machines[0]?.last_location?.lat ?? 0,
        maxLat: machines[0]?.last_location?.lat ?? 0,
        minLng: machines[0]?.last_location?.lng ?? 0,
        maxLng: machines[0]?.last_location?.lng ?? 0,
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
    return (
      machine.last_location.lat >= tempBounds.south &&
      machine.last_location.lat <= tempBounds.north &&
      machine.last_location.lng >= tempBounds.west &&
      machine.last_location.lng <= tempBounds.east
    );
  };

  const selectedMachinesCount = tempBounds
    ? machines.filter((m) => isMachineInBounds(m)).length
    : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="max-h-[90vh] w-[900px] overflow-hidden">
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
              machines within the selected area will be shown.
            </div>

            <div className="h-[400px] rounded-lg border bg-gray-50">
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
                {machines.length > 0 &&
                  machines.map((machine) => (
                    <Marker
                      key={machine.id}
                    position={[
                      machine.last_location.lat,
                      machine.last_location.lng,
                    ]}
                    icon={createMachineIcon(
                      machine,
                       getMachineData(machine.id),
                      isMachineInBounds(machine),
                    )}
                  >
                    <Tooltip>
                      <div className="text-center text-xs font-medium">
                        {machine.name}
                      </div>
                    </Tooltip>
                  </Marker>
                ))}

                {/* Coverage circles for visualization */}
                {machines
                  .filter((m) => isMachineInBounds(m))
                  .map((machine) => (
                    <Circle
                      key={`coverage-${machine.id}`}
                      center={[
                        machine.last_location.lat,
                        machine.last_location.lng,
                      ]}
                      radius={300}
                      pathOptions={{
                        color: '#3b82f6',
                        weight: 1,
                        opacity: 0.3,
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
                  : 'No area selected'}
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
