import { useEffect, useState } from 'react';
import { Polyline } from 'react-leaflet';
import { LatLngExpression } from 'leaflet';

import { Machine } from '@/lib/types/machine';
import { isMachineOnline } from '@/lib/utils';
import './machine-connections.css';

interface MachineConnectionsProps {
  machines: Machine[];
}

interface Connection {
  from: Machine;
  to: Machine;
  positions: LatLngExpression[];
  color: string;
}

export default function MachineConnections({ machines }: MachineConnectionsProps) {
  const [connections, setConnections] = useState<Connection[]>([]);

  useEffect(() => {
    // Find the specific machines by ID
    const machine206 = machines.find(m => m.id === 206);
    const machine207 = machines.find(m => m.id === 207);
    const machine208 = machines.find(m => m.id === 208);

    // If any of the machines are not found, don't render connections
    if (!machine206 || !machine207 || !machine208) {
      setConnections([]);
      return;
    }

    const newConnections: Connection[] = [];

    // Only show connections if both machines are online
    const addConnectionIfOnline = (from: Machine, to: Machine) => {
      if (isMachineOnline(from) && isMachineOnline(to)) {
        const fromPos: LatLngExpression = [
          from.last_location?.lat ?? 12.9716,
          from.last_location?.long ?? 77.5946
        ];
        const toPos: LatLngExpression = [
          to.last_location?.lat ?? 12.9716,
          to.last_location?.long ?? 77.5946
        ];
        newConnections.push({
          from,
          to,
          positions: [fromPos, toPos],
          color: '#10b981', // green for active
        });
      }
    };

    // Only add connections for online machines
    addConnectionIfOnline(machine206, machine207);
    addConnectionIfOnline(machine207, machine208);

    setConnections(newConnections);
  }, [machines]);

  return (
    <>
      {connections.map((connection, index) => (
        <Polyline
          key={`${connection.from.id}-${connection.to.id}-${index}`}
          positions={connection.positions}
          pathOptions={{
            color: connection.color,
            weight: 3,
            opacity: 0.8,
            dashArray: '10, 10',
            lineCap: 'round',
            lineJoin: 'round',
          }}
          className={'animated-dash-line'}
        />
      ))}
    </>
  );
}