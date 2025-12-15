FakeNeighbours = [
        (223,222),
        (222,221),
        (221,225),
        (225,219),
        ]

class Layout:
    self.neighbours = FakeNeighbours
    def __init__(self):
        print(f"Starting fake network with the following neighbours")
        for n in self.neighbours:
            print(n)

    def is_neighbour(self, a, b):
        """
        Checks if two nodes are neighbours.
        """
        return (a,b) in self.neighbours or (b,a) in self.neighbours
