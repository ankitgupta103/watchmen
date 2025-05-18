import constants

class Layout:
    def __init__(self):
        self.inp = constants.node_layout
        self.node_pos = {}
        for i in range(len(self.inp)):
            for j in range(len(self.inp[i])):
                c = self.inp[i][j]
                node_name = f"{c}{c}{c}"
                self.node_pos[node_name] = (i,j)

    def print_layout(self):
        print(self.node_pos)

    def is_neighbour(self, a, b):
        if a not in self.node_pos:
            print(f"{a} not found in layout")
            return False
        if b not in self.node_pos:
            print(f"{b} not found in layout")
            return False
        (ax,ay) = self.node_pos[a]
        (bx,by) = self.node_pos[b]
        return abs(ax-bx)<=1 and abs(ay-by) <= 1

def main():
    l = Layout()
    l.print_layout()
    print(l.is_neighbour("AAA", "BBB"))
    print(l.is_neighbour("AAA", "JJJ"))

if __name__=="__main__":
    main()
