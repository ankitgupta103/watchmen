'use client';

import React, { useEffect, useRef, useState } from 'react';

// --- Type Definitions ---
interface Node {
  id: string;
  position: [number, number]; // [lat, lon]
}

interface Link {
  id: string;
  sourceId: string;
  targetId: string;
  type: string;
}

type NodeStatus = Record<string, 'up' | 'down'>;

type WebSocketMessage =
  | { type: 'INITIAL_LAYOUT'; nodes: Node[] }
  | {
      type: 'COMMUNICATION';
      source: string;
      target: string;
      msg_type: string;
      full_path?: string[];
    }
  | { type: 'STATUS_UPDATE'; nodeId: string; status: 'up' | 'down' };

const linkColors: Record<string, string> = {
  scan: '#1E90FF',
  spath: '#FF4500',
  heartbeat: '#32CD32',
  photo: '#FFD700',
  default: '#999999',
};

const nodeColors: Record<string, string> = {
  up: '#28a745',
  down: '#dc3545',
  central: '#fd7e14',
};

// --- Helper function to load external resources ---
const loadResource = (src: string, type: 'script' | 'link'): Promise<void> => {
  return new Promise((resolve, reject) => {
    if (
      document.querySelector(`${type}[src="${src}"]`) ||
      document.querySelector(`${type}[href="${src}"]`)
    ) {
      resolve();
      return;
    }
    const element = document.createElement(
      type === 'script' ? 'script' : 'link',
    );
    if (type === 'script') {
      (element as HTMLScriptElement).src = src;
      (element as HTMLScriptElement).async = true;
    } else {
      (element as HTMLLinkElement).rel = 'stylesheet';
      (element as HTMLLinkElement).href = src;
    }
    element.onload = () => resolve();
    element.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(element);
  });
};

// --- Main Component ---
const NetworkMap: React.FC = () => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [nodeStatus, setNodeStatus] = useState<NodeStatus>({});
  const [leafletLoaded, setLeafletLoaded] = useState<boolean>(false);
  const [activePath, setActivePath] = useState<string[] | null>(null);
  const [isSimRunning, setIsSimRunning] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected'
  >('connecting');
  const [messageCount, setMessageCount] = useState<number>(0);

  const ws = useRef<WebSocket | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapInstanceRef = useRef<any | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeLayerRef = useRef<any | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkLayerRef = useRef<any | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pathLayerRef = useRef<any | null>(null);
  const pathTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleToggleSimulation = () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const command = !isSimRunning ? 'start' : 'stop';
      ws.current.send(JSON.stringify({ command }));
      setIsSimRunning(!isSimRunning);
    }
  };

  // Load Leaflet resources
  useEffect(() => {
    Promise.all([
      loadResource('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'link'),
      loadResource('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', 'script'),
    ])
      .then(() =>
        loadResource(
          'https://cdnjs.cloudflare.com/ajax/libs/leaflet-polylinedecorator/1.6.0/leaflet.polylinedecorator.min.js',
          'script',
        ),
      )
      .then(() => {
        setLeafletLoaded(true);
      })
      .catch((error) =>
        console.error('Could not load required map libraries:', error),
      );
  }, []);

  // Add custom tooltip styles
  useEffect(() => {
    const styleId = 'leaflet-custom-tooltip-style';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.innerHTML = `
        .leaflet-tooltip.custom-tooltip { 
          background-color: rgba(0, 0, 0, 0.8); 
          border: 1px solid #fff; 
          border-radius: 4px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3); 
          font-weight: bold; 
          color: white; 
          text-shadow: none;
          padding: 4px 8px;
        }
        .leaflet-tooltip.central-tooltip {
          background-color: rgba(253, 126, 20, 0.9);
          border: 2px solid #fff;
          font-weight: bold;
          font-size: 12px;
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  // Initialize map
  useEffect(() => {
    if (!leafletLoaded || !mapContainerRef.current || mapInstanceRef.current)
      return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    const map = L.map(mapContainerRef.current, {
      zoomControl: false,
      maxZoom: 18,
      minZoom: 10,
    }).setView([12.9797, 77.5907], 13);

    mapInstanceRef.current = map;

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      },
    ).addTo(map);

    // Add zoom control to top-right
    L.control.zoom({ position: 'topright' }).addTo(map);

    nodeLayerRef.current = L.layerGroup().addTo(map);
    linkLayerRef.current = L.layerGroup().addTo(map);
    pathLayerRef.current = L.layerGroup().addTo(map);
  }, [leafletLoaded]);

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      setConnectionStatus('connecting');
      ws.current = new WebSocket('ws://127.0.0.1:8000/ws');

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('disconnected');
        setIsSimRunning(false);
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('disconnected');
      };

      ws.current.onmessage = (event) => {
        const data: WebSocketMessage = JSON.parse(event.data);
        setMessageCount((prev) => prev + 1);

        switch (data.type) {
          case 'INITIAL_LAYOUT':
            setNodes(data.nodes);
            setNodeStatus(
              data.nodes.reduce(
                (acc, node) => ({ ...acc, [node.id]: 'up' }),
                {},
              ),
            );
            console.log(`Loaded ${data.nodes.length} nodes`);
            break;

          case 'COMMUNICATION':
            const linkId = `${data.source}-${data.target}-${Date.now()}`;
            setLinks((prev) => [
              ...prev,
              {
                id: linkId,
                sourceId: data.source,
                targetId: data.target,
                type: data.msg_type,
              },
            ]);

            // Remove link after animation duration
            setTimeout(
              () => setLinks((prev) => prev.filter((l) => l.id !== linkId)),
              1500,
            );

            // Show full path if available
            if (data.full_path && data.full_path.length > 1) {
              if (pathTimeoutRef.current) clearTimeout(pathTimeoutRef.current);
              setActivePath(data.full_path);
              pathTimeoutRef.current = setTimeout(
                () => setActivePath(null),
                2500,
              );
            }
            break;

          case 'STATUS_UPDATE':
            setNodeStatus((prev) => ({ ...prev, [data.nodeId]: data.status }));
            break;
        }
      };
    };

    connectWebSocket();

    return () => {
      ws.current?.close();
      if (pathTimeoutRef.current) clearTimeout(pathTimeoutRef.current);
    };
  }, []);

  // Update nodes on map
  useEffect(() => {
    if (!leafletLoaded || !nodeLayerRef.current) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    nodeLayerRef.current.clearLayers();

    nodes.forEach((node) => {
      const status = nodeStatus[node.id] || 'up';
      const isCentral = node.id === 'ZZZ';
      const color = isCentral
        ? nodeColors.central
        : status === 'up'
          ? nodeColors.up
          : nodeColors.down;

      const marker = L.circleMarker(node.position, {
        radius: isCentral ? 12 : 8,
        color: '#fff',
        weight: 2,
        fillColor: color,
        fillOpacity: 0.9,
      }).bindTooltip(isCentral ? `${node.id} (Central)` : node.id, {
        permanent: true,
        direction: 'top',
        offset: [0, isCentral ? -15 : -10],
        className: isCentral
          ? 'custom-tooltip central-tooltip'
          : 'custom-tooltip',
      });

      nodeLayerRef.current.addLayer(marker);
    });

    // Fit bounds to show all nodes
    if (nodes.length > 0 && mapInstanceRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const L = (window as any).L;
      const bounds = L.latLngBounds(nodes.map((n) => n.position));
      mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [nodes, nodeStatus, leafletLoaded]);

  // Update links on map
  useEffect(() => {
    if (!leafletLoaded || !linkLayerRef.current) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    linkLayerRef.current.clearLayers();

    links.forEach((link) => {
      const sourceNode = nodes.find((n) => n.id === link.sourceId);
      const targetNode = nodes.find((n) => n.id === link.targetId);

      if (sourceNode && targetNode) {
        const color = linkColors[link.type] || linkColors.default;
        const polyline = L.polyline(
          [sourceNode.position, targetNode.position],
          {
            color: color,
            weight: 3,
            opacity: 0.8,
            className: 'communication-link',
          },
        );

        linkLayerRef.current.addLayer(polyline);

        // Add arrow decorator to show direction
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if ((window as any).L.polylineDecorator) {
          L.polylineDecorator(polyline, {
            patterns: [
              {
                offset: '70%',
                repeat: 0,
                symbol: L.Symbol.arrowHead({
                  pixelSize: 15,
                  polygon: false,
                  pathOptions: {
                    stroke: true,
                    weight: 2,
                    color: color,
                    fillOpacity: 1,
                    fillColor: color,
                  },
                }),
              },
            ],
          }).addTo(linkLayerRef.current);
        }
      }
    });
  }, [links, nodes, leafletLoaded]);

  // Update active path visualization
  useEffect(() => {
    if (!leafletLoaded || !pathLayerRef.current) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    pathLayerRef.current.clearLayers();

    if (activePath && activePath.length > 1) {
      const pathPositions = activePath
        .map((nodeId) => nodes.find((n) => n.id === nodeId)?.position)
        .filter((p): p is [number, number] => p !== undefined);

      if (pathPositions.length > 1) {
        const pathPolyline = L.polyline(pathPositions, {
          color: '#fef08a',
          weight: 8,
          opacity: 0.9,
          dashArray: '10, 5',
        });

        pathLayerRef.current.addLayer(pathPolyline);

        // Add arrows to show direction along the path
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if ((window as any).L.polylineDecorator) {
          L.polylineDecorator(pathPolyline, {
            patterns: [
              {
                offset: 25,
                repeat: 80,
                symbol: L.Symbol.arrowHead({
                  pixelSize: 18,
                  pathOptions: {
                    color: '#fef08a',
                    fillOpacity: 1,
                    weight: 0,
                    fillColor: '#fef08a',
                  },
                }),
              },
            ],
          }).addTo(pathLayerRef.current);
        }
      }
    }
  }, [activePath, nodes, leafletLoaded]);

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'disconnected':
        return 'bg-red-500';
    }
  };

  return (
    <div className="relative h-screen w-screen bg-gray-900">
      <div ref={mapContainerRef} className="h-full w-full" />

      {!leafletLoaded && (
        <div className="bg-opacity-80 absolute inset-0 z-[1001] flex items-center justify-center bg-gray-900 text-white">
          <div className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-white"></div>
            <div>Loading Map Resources...</div>
          </div>
        </div>
      )}

      {/* Connection Status */}
      <div className="bg-opacity-70 absolute top-4 left-4 z-[1000] rounded-lg bg-black px-3 py-2 text-white">
        <div className="flex items-center space-x-2">
          <div
            className={`h-3 w-3 rounded-full ${getConnectionStatusColor()}`}
          ></div>
          <span className="text-sm font-medium">
            {connectionStatus.charAt(0).toUpperCase() +
              connectionStatus.slice(1)}
          </span>
        </div>
        <div className="mt-1 text-xs text-gray-300">
          Messages: {messageCount}
        </div>
      </div>

      {/* Legend */}
      <div className="bg-opacity-80 absolute top-4 right-4 z-[1000] max-w-xs rounded-lg bg-black p-4 text-white">
        <h3 className="mb-3 text-sm font-bold">Network Legend</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center space-x-2">
            <div className="h-4 w-4 rounded-full bg-orange-500"></div>
            <span>Command Central (ZZZ)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-4 w-4 rounded-full bg-green-500"></div>
            <span>Device (Online)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-4 w-4 rounded-full bg-red-500"></div>
            <span>Device (Offline)</span>
          </div>
          <hr className="border-gray-600" />
          <div className="flex items-center space-x-2">
            <div className="h-1 w-6 bg-blue-500"></div>
            <span>Scan Message</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-1 w-6 bg-orange-500"></div>
            <span>Shortest Path</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-1 w-6 bg-green-500"></div>
            <span>Heartbeat</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-1 w-6 bg-yellow-500"></div>
            <span>Photo/Event</span>
          </div>
          <div className="flex items-center space-x-2">
            <div
              className="h-1 w-6 bg-yellow-300"
              style={{ background: 'dashed' }}
            ></div>
            <span>Active Path</span>
          </div>
        </div>
      </div>

      {/* Simulation Control */}
      <div className="absolute bottom-5 left-1/2 z-[1000] -translate-x-1/2">
        <button
          onClick={handleToggleSimulation}
          disabled={connectionStatus !== 'connected'}
          className={`transform rounded-lg px-8 py-4 font-bold text-white shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 ${
            isSimRunning
              ? 'bg-red-600 hover:bg-red-700'
              : 'bg-green-600 hover:bg-green-700'
          }`}
        >
          {isSimRunning ? 'Stop Simulation' : 'Start Simulation'}
        </button>
      </div>

      {/* Node count display */}
      <div className="bg-opacity-70 absolute bottom-5 left-4 z-[1000] rounded-lg bg-black px-3 py-2 text-sm text-white">
        Nodes: {nodes.length} | Active Links: {links.length}
      </div>
    </div>
  );
};

export default NetworkMap;
