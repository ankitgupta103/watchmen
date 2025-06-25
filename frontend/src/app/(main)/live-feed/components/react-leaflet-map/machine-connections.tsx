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
  isActive: boolean;
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

    // Check online status
    const is206Online = isMachineOnline(machine206);
    const is207Online = isMachineOnline(machine207);
    // const is208Online = true; // 208 is always online

    // Helper function to create connection
    const createConnection = (from: Machine, to: Machine, isActive: boolean = true) => {
      const fromPos: LatLngExpression = [
        from.last_location?.lat ?? 12.9716,
        from.last_location?.long ?? 77.5946
      ];
      const toPos: LatLngExpression = [
        to.last_location?.lat ?? 12.9716,
        to.last_location?.long ?? 77.5946
      ];

      return {
        from,
        to,
        positions: [fromPos, toPos],
        color: isActive ? (isMachineOnline(from) && isMachineOnline(to) ? '#10b981' : '#ef4444') : '#6b7280',
        isActive
      };
    };

    // Connection logic based on online status
    if (is206Online && is207Online) {
      // Normal case: 206 -> 207 -> 208
      newConnections.push(createConnection(machine206, machine207));
      newConnections.push(createConnection(machine207, machine208));
    } else if (is206Online && !is207Online) {
      // 207 is offline
      newConnections.push(createConnection(machine206, machine207, false));
      newConnections.push(createConnection(machine206, machine208, false));
    } else if (!is206Online && is207Online) {
      // 206 is offline: 207 -> 208
      newConnections.push(createConnection(machine207, machine208));
      // Show inactive connection from 206
      newConnections.push(createConnection(machine206, machine207, false));
    } else {
      // Both 206 and 207 are offline: show all as inactive
      newConnections.push(createConnection(machine206, machine207, false));
      newConnections.push(createConnection(machine207, machine208, false));
      // Also show direct connection from 208 perspective (reversed)
      newConnections.push(createConnection(machine208, machine206, false));
    }

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
            opacity: connection.isActive ? 0.8 : 0.4,
            dashArray: '10, 10',
            lineCap: 'round',
            lineJoin: 'round',
          }}
          className={connection.isActive ? 'animated-dash-line' : 'inactive-dash-line'}
        />
      ))}
      

    </>
  );
}