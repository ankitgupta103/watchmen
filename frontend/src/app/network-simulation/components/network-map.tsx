'use client';

import React, { useEffect, useRef, useState } from 'react';
// Import Leaflet and its CSS from the installed npm package
import L from 'leaflet';

import 'leaflet/dist/leaflet.css';

// --- Type Definitions ---
interface Node {
  id: string;
  position: [number, number];
  latlng: [number, number];
}

interface Link {
  id: string;
  sourceId: string;
  targetId: string;
  type: string;
}

interface LogEntry {
  timestamp: string;
  message: string;
}

type NodeStatus = Record<string, 'up' | 'down'>;
type NodeInfo = Record<string, { neighbours: string[] }>;

type WebSocketMessage =
  | {
      type: 'INITIAL_LAYOUT';
      nodes: Array<{ id: string; position: [number, number] }>;
    }
  | {
      type: 'COMMUNICATION';
      source: string;
      target: string;
      msg_type: string;
      msg: {
        neighbours?: string[];
        source?: string;
      };
      full_path?: string[];
    }
  | { type: 'STATUS_UPDATE'; nodeId: string; status: 'up' | 'down' }
  | { type: 'log_message'; message: string; timestamp: number };

// --- Constants ---
const BANGALORE_CENTER: [number, number] = [12.9716, 77.5946];
const MAP_ZOOM_LEVEL = 13;
const COORD_SCALE_FACTOR = 0.015;

const COLORS = {
  link: {
    scan: '#1E90FF',
    spath: '#FF4500',
    heartbeat: '#32CD32',
    photo: '#FFD700',
    default: '#999999',
    activePath: '#fef08a',
    neighbor: '#00fffb', // Light gray for permanent neighbor connections
  },
  node: {
    up: '#28a745',
    down: '#dc3545',
    central: '#fd7e14',
    border: '#FFFFFF',
  },
};

// --- Main Component ---
const NetworkMap: React.FC = () => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [activePath, setActivePath] = useState<string[] | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [nodeStatus, setNodeStatus] = useState<NodeStatus>({});
  const [nodeInfo, setNodeInfo] = useState<NodeInfo>({});
  const [currentPhase, setCurrentPhase] = useState<string>('Simulation Paused');
  const [isSimRunning, setIsSimRunning] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected'
  >('connecting');

  const ws = useRef<WebSocket | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const nodeLayerRef = useRef<L.LayerGroup | null>(null);
  const linkLayerRef = useRef<L.LayerGroup | null>(null);
  const neighborLayerRef = useRef<L.LayerGroup | null>(null); // New layer for permanent neighbor connections
  const pathLayerRef = useRef<L.LayerGroup | null>(null);
  const logContainerRef = useRef<HTMLDivElement | null>(null);
  const activePathTimeout = useRef<NodeJS.Timeout | null>(null);

  const projectGridToLatLng = (
    gridNodes: Array<{ id: string; position: [number, number] }>,
  ): Node[] => {
    if (gridNodes.length === 0) return [];
    let avgX = 0,
      avgY = 0;
    gridNodes.forEach((n) => {
      avgX += n.position[0];
      avgY += n.position[1];
    });
    avgX /= gridNodes.length;
    avgY /= gridNodes.length;

    return gridNodes.map(({ id, position }) => {
      const lon =
        BANGALORE_CENTER[1] + (position[0] - avgX) * COORD_SCALE_FACTOR;
      const lat =
        BANGALORE_CENTER[0] - (position[1] - avgY) * COORD_SCALE_FACTOR * 0.8;
      return { id, position, latlng: [lat, lon] };
    });
  };

  // Effect to initialize the map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: BANGALORE_CENTER,
      zoom: MAP_ZOOM_LEVEL,
      zoomControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      touchZoom: false,
    });

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {
        attribution:
          '&copy; <a href="https://carto.com/attributions">CARTO</a>',
      },
    ).addTo(map);

    mapInstanceRef.current = map;
    nodeLayerRef.current = L.layerGroup().addTo(map);
    neighborLayerRef.current = L.layerGroup().addTo(map); // Initialize neighbor layer
    linkLayerRef.current = L.layerGroup().addTo(map);
    pathLayerRef.current = L.layerGroup().addTo(map);

    // Add custom styles for our node markers, tooltips, and pulse animations
    const style = document.createElement('style');
    style.innerHTML = `
      .custom-node-label { font-size: 12px; font-weight: bold; color: white; text-shadow: 0 0 3px black; text-align: center; width: 50px; line-height: 1; }
      .custom-node-marker { position: relative; display: flex; flex-direction: column; align-items: center; }
      .node-circle { border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px black; }
      .hover-tooltip { background-color: rgba(0, 0, 0, 0.8) !important; border: 1px solid #fff !important; color: white !important; }
      
      /* Pulse animation styles */
      @keyframes pulse-flow {
        0% { stroke-dashoffset: 100%; opacity: 0.8; }
        50% { opacity: 1; }
        100% { stroke-dashoffset: 0%; opacity: 0.3; }
      }
      
      .neighbor-pulse {
        stroke-dasharray: 8 4;
        animation: pulse-flow 3s ease-in-out infinite;
      }
      
      .neighbor-pulse:nth-child(odd) {
        animation-delay: 1.5s;
      }
    `;
    document.head.appendChild(style);
  }, []);

  // Effect for WebSocket connection
  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket('ws://127.0.0.1:8000/ws');
      ws.current.onopen = () => setConnectionStatus('connected');
      ws.current.onclose = () => {
        setConnectionStatus('disconnected');
        setIsSimRunning(false);
        setTimeout(connect, 3000);
      };
      ws.current.onmessage = (event) => {
        const data: WebSocketMessage = JSON.parse(event.data);
        switch (data.type) {
          case 'INITIAL_LAYOUT':
            setNodes(projectGridToLatLng(data.nodes));
            setNodeStatus(
              data.nodes.reduce(
                (acc, node) => ({ ...acc, [node.id]: 'up' }),
                {},
              ),
            );
            break;
          case 'COMMUNICATION': {
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
            setTimeout(
              () => setLinks((prev) => prev.filter((l) => l.id !== linkId)),
              1500,
            );

            if (data.full_path) {
              if (activePathTimeout.current)
                clearTimeout(activePathTimeout.current);
              setActivePath(data.full_path);
              activePathTimeout.current = setTimeout(
                () => setActivePath(null),
                2500,
              );
            }

            // This is where neighbor info is received
            if (
              data.msg_type === 'heartbeat' &&
              data.msg.source &&
              data.msg.neighbours
            ) {
              setNodeInfo((prev) => ({
                ...prev,
                [data.msg.source as string]: {
                  neighbours: data.msg.neighbours as string[],
                },
              }));
            }
            break;
          }
          case 'STATUS_UPDATE':
            // This is where offline status is received
            setNodeStatus((prev) => ({ ...prev, [data.nodeId]: data.status }));
            
            // Clear neighbors when node goes offline
            if (data.status === 'down') {
              setNodeInfo((prev) => ({
                ...prev,
                [data.nodeId]: { neighbours: [] }
              }));
            }
            break;
          case 'log_message': {
            const newLog: LogEntry = {
              timestamp: new Date(data.timestamp * 1000).toLocaleTimeString(),
              message: data.message,
            };
            setLogs((prev) => [...prev.slice(-200), newLog]);
            if (data.message.startsWith('SIM_PHASE:')) {
              setCurrentPhase(data.message.replace('SIM_PHASE: ', ''));
            } else if (data.message.startsWith('CONTROL: Simulation paused')) {
              setCurrentPhase('Simulation Paused');
            }
            break;
          }
        }
      };
    };
    connect();
    return () => {
      ws.current?.close();
      if (activePathTimeout.current) clearTimeout(activePathTimeout.current);
    };
  }, []);

  // Effect for drawing permanent neighbor connections
  useEffect(() => {
    if (!neighborLayerRef.current || !nodes.length) return;
    neighborLayerRef.current.clearLayers();

    // Build a set of all unique neighbor connections
    const neighborConnections = new Set<string>();
    
    Object.entries(nodeInfo).forEach(([nodeId, info]) => {
      info.neighbours.forEach((neighborId) => {
        // Create a unique key for each connection (sorted to avoid duplicates)
        const connectionKey = [nodeId, neighborId].sort().join('-');
        neighborConnections.add(connectionKey);
      });
    });

    // Draw the neighbor connections
    neighborConnections.forEach((connectionKey) => {
      const [nodeId1, nodeId2] = connectionKey.split('-');
      const node1 = nodes.find((n) => n.id === nodeId1);
      const node2 = nodes.find((n) => n.id === nodeId2);

      if (node1 && node2 && neighborLayerRef.current) {
        // Create a subtle line for the neighbor connection
        const neighborLine = L.polyline([node1.latlng, node2.latlng], {
          color: COLORS.link.neighbor,
          weight: 1.5,
          opacity: 0.4,
          className: 'neighbor-pulse', // Add pulse animation class
        });

        neighborLayerRef.current.addLayer(neighborLine);
      }
    });
  }, [nodes, nodeInfo]);

  // --- CRITICAL FIX: This single hook now handles all node drawing. ---
  // It correctly depends on `nodes`, `nodeStatus`, and `nodeInfo`.
  // Any change to these states will trigger this effect and redraw the nodes.
  useEffect(() => {
    if (!nodeLayerRef.current) return;
    nodeLayerRef.current.clearLayers();

    nodes.forEach((node) => {
      const isCentral = node.id === 'ZZZ';
      // Get the most recent status, default to 'up'
      const status = nodeStatus[node.id] || 'up';
      const color = isCentral ? COLORS.node.central : COLORS.node[status];
      const size = isCentral ? 24 : 16;

      // Create the HTML for the custom marker icon
      const iconHtml = `
            <div class="custom-node-marker">
                <div class="custom-node-label">${node.id}</div>
                <div class="node-circle" style="width: ${size}px; height: ${size}px; background-color: ${color};"></div>
            </div>
        `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: '', // important to clear default leaflet styles
        iconSize: [50, 40],
        iconAnchor: [25, 20], // Anchor point of the icon
      });

      // Get the most recent neighbor info
      const neighbors = nodeInfo[node.id]?.neighbours || [];
      const tooltipContent = `
            <div class="font-bold">Neighbors:</div>
            <div>${neighbors.length > 0 ? neighbors.join(', ') : 'None detected'}</div>
        `;

      const marker = L.marker(node.latlng, { icon: customIcon }).bindTooltip(
        tooltipContent,
        { className: 'hover-tooltip', offset: [0, -20] },
      );

      nodeLayerRef?.current?.addLayer(marker);
    });
  }, [nodes, nodeStatus, nodeInfo]); // This dependency array is key to fixing the bugs

  // Effect for drawing ephemeral links
  useEffect(() => {
    if (!linkLayerRef.current || !nodes.length) return;
    linkLayerRef.current.clearLayers();

    links.forEach((link) => {
      const sourceNode = nodes.find((n) => n.id === link.sourceId);
      const targetNode = nodes.find((n) => n.id === link.targetId);

      if (sourceNode && targetNode && linkLayerRef.current) {
        L.polyline([sourceNode.latlng, targetNode.latlng], {
          color:
            COLORS.link[link.type as keyof typeof COLORS.link] ||
            COLORS.link.default,
          weight: 3,
          opacity: 0.9,
        }).addTo(linkLayerRef.current);
      }
    });
  }, [links, nodes]);

  // Effect for drawing the highlighted active path
  useEffect(() => {
    if (!pathLayerRef.current || !nodes.length) return;
    pathLayerRef.current.clearLayers();

    if (activePath && activePath.length > 1) {
      const pathPositions = activePath
        .map((nodeId) => nodes.find((n) => n.id === nodeId)?.latlng)
        .filter((p): p is [number, number] => p !== undefined);

      if (pathPositions.length > 1) {
        L.polyline(pathPositions, {
          color: COLORS.link.activePath,
          weight: 6,
          opacity: 0.9,
          dashArray: '10, 5',
        }).addTo(pathLayerRef.current);
      }
    }
  }, [activePath, nodes]);

  // Effect for auto-scrolling the log panel
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Handler to start/stop the simulation
  const handleToggleSimulation = () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const command = !isSimRunning ? 'start' : 'stop';
      ws.current.send(JSON.stringify({ command }));
      setIsSimRunning(!isSimRunning);
      if (command === 'stop') {
        setCurrentPhase('Simulation Paused');
      }
    }
  };

  return (
    <div className="flex h-screen w-screen bg-gray-900 font-sans text-gray-200">
      <div className="relative h-full flex-grow">
        <div ref={mapContainerRef} className="h-full w-full" />
        <div className="pointer-events-none absolute top-0 right-0 left-0 z-[1000] p-4">
          <div className="w-full text-center">
            <div className="bg-opacity-70 inline-block rounded-lg bg-black px-6 py-2">
              <p className="text-sm text-gray-400">CURRENT PHASE</p>
              <p className="text-xl font-bold text-amber-400">{currentPhase}</p>
            </div>
          </div>
        </div>
        <div className="bg-opacity-70 pointer-events-auto absolute top-4 right-4 z-[1000] rounded-lg bg-black p-4">
          <h3 className="mb-3 text-lg font-bold">Legend</h3>
          <div className="space-y-3 text-sm">
            <div>
              <h4 className="mb-1 font-semibold text-gray-300">Node Status</h4>
              <div className="flex items-center">
                <div
                  className="mr-2 h-4 w-4 rounded-full"
                  style={{ backgroundColor: COLORS.node.central }}
                ></div>
                Command Central
              </div>
              <div className="flex items-center">
                <div
                  className="mr-2 h-4 w-4 rounded-full"
                  style={{ backgroundColor: COLORS.node.up }}
                ></div>
                Device (Online)
              </div>
              <div className="flex items-center">
                <div
                  className="mr-2 h-4 w-4 rounded-full"
                  style={{ backgroundColor: COLORS.node.down }}
                ></div>
                Device (Offline)
              </div>
            </div>
            <div>
              <h4 className="mb-1 font-semibold text-gray-300">
                Communication
              </h4>
              <div className="flex items-center">
                <div
                  className="mr-2 h-1 w-6"
                  style={{ backgroundColor: COLORS.link.neighbor }}
                ></div>
                Neighbor Link
              </div>
              <div className="flex items-center">
                <div
                  className="mr-2 h-1 w-6"
                  style={{ backgroundColor: COLORS.link.scan }}
                ></div>
                Scan Message
              </div>
              <div className="flex items-center">
                <div
                  className="mr-2 h-1 w-6"
                  style={{ backgroundColor: COLORS.link.spath }}
                ></div>
                Shortest Path
              </div>
              <div className="flex items-center">
                <div
                  className="mr-2 h-1 w-6"
                  style={{ backgroundColor: COLORS.link.heartbeat }}
                ></div>
                Heartbeat
              </div>
              <div className="flex items-center">
                <div
                  className="mr-2 h-2 w-6 border-2 border-dashed"
                  style={{ borderColor: COLORS.link.activePath }}
                ></div>
                Active Message Path
              </div>
            </div>
          </div>
        </div>
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
            {isSimRunning ? 'Pause Simulation' : 'Start Simulation'}
          </button>
        </div>
      </div>
      <div className="flex h-full w-[450px] flex-col border-l border-gray-600 bg-gray-800 shadow-lg">
        <h2 className="flex items-center justify-between border-b border-gray-600 p-3 text-lg font-bold">
          <span>Event Log</span>
          <div className={`flex items-center space-x-2 text-sm`}>
            <div
              className={`h-3 w-3 rounded-full ${connectionStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'}`}
            ></div>
            <span>{connectionStatus}</span>
          </div>
        </h2>
        <div
          ref={logContainerRef}
          className="flex-grow overflow-y-auto p-3 font-mono text-xs"
        >
          {logs.map((log, index) => (
            <div key={index} className="flex">
              <span className="mr-2 flex-shrink-0 text-gray-500">
                {log.timestamp}
              </span>
              <p className="break-words text-gray-300">{log.message}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default NetworkMap;