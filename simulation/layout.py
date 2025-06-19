import constants

class Layout:
    def __init__(self):
        """
        Initializes the layout from the grid defined in constants.
        Node positions are stored as (row, col) tuples.
        """
        self.inp = constants.node_layout
        self.node_pos = {}
        for r, row_list in enumerate(self.inp):
            for c, char in enumerate(row_list):
                node_name = f"{char}{char}{char}"
                self.node_pos[node_name] = (r, c)
        
        self.node_pos[constants.CENTRAL_NODE_ID] = (4, 5)
        
        self.gateway_nodes = ["JJJ", "KKK"]

    def get_all_nodes(self):
        """
        Returns a list of all nodes with their ID and grid position.
        The position is returned as [x, y] for frontend convenience.
        """
        nodes = []
        for node_id, (r, c) in self.node_pos.items():
            nodes.append({"id": node_id, "position": [c, r]}) # [x, y] format
        return nodes

    def is_neighbour(self, a, b):
        """
        Checks if two nodes are neighbours. Neighbours are adjacent in the grid,
        including diagonals. A special rule connects the gateways to central command.
        """
        if (a in self.gateway_nodes and b == constants.CENTRAL_NODE_ID) or \
           (b in self.gateway_nodes and a == constants.CENTRAL_NODE_ID):
            return True
            
        if a == constants.CENTRAL_NODE_ID or b == constants.CENTRAL_NODE_ID:
            return False # Central node is only connected to the gateways
            
        if a not in self.node_pos or b not in self.node_pos:
            return False
            
        (ar, ac) = self.node_pos[a]
        (br, bc) = self.node_pos[b]
        # Nodes are neighbours if their row/col distance is at most 1
        return abs(ar - br) <= 1 and abs(ac - bc) <= 1 and a != b

    def list_nodes(self):
        """Returns a list of all node IDs."""
        return list(self.node_pos.keys())

    def get_neighbours(self, a):
        """Returns a list of all neighbours for a given node 'a'."""
        neighbours = []
        all_nodes = self.list_nodes()
        for n in all_nodes:
            if self.is_neighbour(a, n):
                neighbours.append(n)
        return neighbours