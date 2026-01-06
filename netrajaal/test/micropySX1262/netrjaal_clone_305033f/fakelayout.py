FakeNeighbours = [
        (225,222),
        (222,221),
        (221,225),
        (223,219),
        ]

class Layout:        
    def __init__(self):
        self.neighbours = FakeNeighbours
        print(f"Starting fake network with the following neighbours")
        for n in self.neighbours:
            print(n)

    def is_neighbour(self, a, b):
        """
        Checks if two nodes are neighbours.
        """
        return (a,b) in self.neighbours or (b,a) in self.neighbours
