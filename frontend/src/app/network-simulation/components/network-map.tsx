'use client';

import React, { useState, useEffect, useRef } from 'react';

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
  | { type: 'COMMUNICATION'; source: string; target: string; msg_type: string; full_path?: string[] }
  | { type: 'STATUS_UPDATE'; nodeId: string; status: 'up' | 'down' };
  
  const linkColors: Record<string, string> = { scan: '#1E90FF', spath: '#FF4500', heartbeat: '#32CD32', photo: '#FFD700', default: '#999999' };
  const nodeColors: Record<string, string> = { up: '#28a745', down: '#dc3545', central: '#fd7e14' };

  // --- Helper function to load external resources ---
const loadResource = (src: string, type: 'script' | 'link'): Promise<void> => {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`${type}[src="${src}"]`)) {
      resolve();
      return;
    }
    const element = document.createElement(type === 'script' ? 'script' : 'link');
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

  useEffect(() => {
    Promise.all([
      loadResource('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'link'),
      loadResource('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', 'script')
    ]).then(() => {
      setLeafletLoaded(true);
    }).catch(error => console.error("Could not load Leaflet library:", error));
  }, []);

  useEffect(() => {
    const styleId = 'leaflet-custom-tooltip-style';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.innerHTML = `.leaflet-tooltip.custom-tooltip { background-color: transparent; border: none; box-shadow: none; font-weight: bold; color: white; text-shadow: 1px 1px 2px black; }`;
        document.head.appendChild(style);
    }
  }, []);

  useEffect(() => {
    if (!leafletLoaded || !mapContainerRef.current || mapInstanceRef.current) return;
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    const map = L.map(mapContainerRef.current, { zoomControl: false }).setView([12.9797, 77.5907], 13);
    mapInstanceRef.current = map;
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);

    nodeLayerRef.current = L.layerGroup().addTo(map);
    linkLayerRef.current = L.layerGroup().addTo(map);
    pathLayerRef.current = L.layerGroup().addTo(map);
  }, [leafletLoaded]);

  useEffect(() => {
    ws.current = new WebSocket('ws://127.0.0.1:8000/ws');
    ws.current.onopen = () => console.log('WebSocket connected');
    ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsSimRunning(false);
    }

    ws.current.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      switch (data.type) {
        case 'INITIAL_LAYOUT':
          setNodes(data.nodes);
          setNodeStatus(data.nodes.reduce((acc, node) => ({...acc, [node.id]: 'up'}), {}));
          break;
        case 'COMMUNICATION':
          const linkId = `${data.source}-${data.target}-${Date.now()}`;
          setLinks(prev => [...prev, { id: linkId, sourceId: data.source, targetId: data.target, type: data.msg_type }]);
          setTimeout(() => setLinks(prev => prev.filter(l => l.id !== linkId)), 1000);

          if (data.full_path && data.full_path.length > 1) {
              if(pathTimeoutRef.current) clearTimeout(pathTimeoutRef.current);
              setActivePath(data.full_path);
              pathTimeoutRef.current = setTimeout(() => setActivePath(null), 2000);
          }
          break;
        case 'STATUS_UPDATE':
          setNodeStatus(prev => ({ ...prev, [data.nodeId]: data.status }));
          break;
      }
    };

    return () => {
        ws.current?.close();
        if(pathTimeoutRef.current) clearTimeout(pathTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (!leafletLoaded || !nodeLayerRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    nodeLayerRef.current.clearLayers();
    nodes.forEach(node => {
        const status = nodeStatus[node.id] || 'up';
        const isCentral = node.id === 'ZZZ';
        const color = isCentral ? nodeColors.central : (status === 'up' ? nodeColors.up : nodeColors.down);
        const marker = L.circleMarker(node.position, { radius: 8, color, fillColor: color, fillOpacity: 0.9 })
            .bindTooltip(node.id, { permanent: true, direction: 'top', offset: [0, -10], className: 'custom-tooltip' });
        nodeLayerRef.current.addLayer(marker);
    });
     if (nodes.length > 0 && mapInstanceRef.current) {
            const bounds = L.latLngBounds(nodes.map(n => n.position));
            mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50] });
        }
  }, [nodes, nodeStatus, leafletLoaded, nodeColors]);

  useEffect(() => {
    if (!leafletLoaded || !linkLayerRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    linkLayerRef.current.clearLayers();
    links.forEach(link => {
        const sourceNode = nodes.find(n => n.id === link.sourceId);
        const targetNode = nodes.find(n => n.id === link.targetId);
        if (sourceNode && targetNode) {
            linkLayerRef.current.addLayer(L.polyline([sourceNode.position, targetNode.position], { color: linkColors[link.type] || linkColors.default, weight: 2.5, opacity: 0.8 }));
        }
    });
  }, [links, nodes, leafletLoaded, linkColors]);

  useEffect(() => {
    if (!leafletLoaded || !pathLayerRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const L = (window as any).L;
    pathLayerRef.current.clearLayers();
    if (activePath && activePath.length > 1) {
        const pathPositions = activePath.map(nodeId => nodes.find(n => n.id === nodeId)?.position).filter((p): p is [number, number] => p !== undefined);
        if (pathPositions.length > 1) {
            pathLayerRef.current.addLayer(L.polyline(pathPositions, { color: '#fef08a', weight: 6, opacity: 0.9 }));
        }
    }
  }, [activePath, nodes, leafletLoaded]);

  return (
    <div className="relative h-screen w-screen">
      <div ref={mapContainerRef} className="h-full w-full bg-gray-900" />
      {!leafletLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-80 text-white z-[1001]">
          Loading Map...
        </div>
      )}
      <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-[1000]">
        <button
          onClick={handleToggleSimulation}
          className={`px-6 py-3 rounded-lg font-bold text-white shadow-lg transition-transform transform hover:scale-105 ${
            isSimRunning ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
          }`}
        >
          {isSimRunning ? 'Stop Simulation' : 'Start Simulation'}
        </button>
      </div>
    </div>
  );
};

export default NetworkMap;
