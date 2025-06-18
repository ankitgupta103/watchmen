import math

class Layout:
    """
    This class defines the static layout of the network and assigns geographical coordinates.
    """
    def __init__(self, num_devices=26):
        # Central point for our map (e.g., Vidhana Soudha, Bengaluru)
        self.center_lat = 12.9797
        self.center_lon = 77.5907
        self.nodes = {}
        self.num_devices = num_devices
        self._generate_grid_layout()
        self._assign_neighbours()

    def _generate_grid_layout(self):
        """
        Arranges nodes in a grid to ensure they are spaced out.
        The letters 'A' through 'Y' are for devices, and 'Z' is for the central command.
        """
        size = math.ceil(math.sqrt(self.num_devices))
        spacing = 0.01  # Spacing in latitude/longitude degrees
        
        for i in range(self.num_devices):
            char_code = i + 65
            devid = f"{chr(char_code)}{chr(char_code)}{chr(char_code)}"
            
            row = i // size
            col = i % size
            
            lat = self.center_lat + (row - size / 2) * spacing
            lon = self.center_lon + (col - size / 2) * spacing
            
            self.nodes[devid] = {
                "id": devid,
                "lat": lat,
                "lon": lon,
                "neighbours": []
            }
        
        # Add the command central
        self.nodes["ZZZ"] = {
            "id": "ZZZ",
            "lat": self.center_lat + 0.01,
            "lon": self.center_lon - 0.02,
            "neighbours": []
        }

    def _assign_neighbours(self):
        """
        Assigns neighbours based on proximity in the grid.
        A node's neighbours are the ones directly adjacent (horizontally, vertically, diagonally).
        """
        node_ids = list(self.nodes.keys())
        for node_id1 in node_ids:
            for node_id2 in node_ids:
                if node_id1 == node_id2:
                    continue
                
                node1 = self.nodes[node_id1]
                node2 = self.nodes[node_id2]
                
                # Simple distance check for neighborhood
                dist = math.sqrt((node1['lat'] - node2['lat'])**2 + (node1['lon'] - node2['lon'])**2)
                
                # A threshold slightly larger than the grid spacing defines neighbors
                if dist < 0.015:
                    if node_id2 not in node1['neighbours']:
                        node1['neighbours'].append(node_id2)
                    if node_id1 not in node2['neighbours']:
                        node2['neighbours'].append(node_id1)


    def get_neighbours(self, devid):
        return self.nodes.get(devid, {}).get('neighbours', [])

    def get_all_nodes(self):
        return [
            {"id": data["id"], "position": [data["lat"], data["lon"]]}
            for data in self.nodes.values()
        ]
