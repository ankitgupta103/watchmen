import time
import os

class CommandCentral:
    def __init__(self):
        self.node_list = []

    def init_listener(self):
        read_from_file("network_sim.txt")
        pass

    def print_node_info(self, node):
        print(node)

    def print_map(self):
        for n in self.node_list:
            self.print_node_info(n)

def main():
    print(f" === Welcome to Central Command ====")
    cc = CommandCentral()
    cc.init

if __name__=="__main__":
    main()
