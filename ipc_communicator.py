import time
import os
import threading
import constants
import json
import layout
import glob
import random

class IPCCommunicator:
    def __init__(self):
        # This is a simulated network layout, it is only used to "receive" messages which a real network can see.
        self.simulated_layout = layout.Layout()
        self.dev = {} # ID -> Obj
        self.robustness = 0.99

    def add_dev(self, devid, devobj):
        self.dev[devid] = devobj
        print(f"Added {len(self.dev)} devs")

    # Send msg of mtype to dest, None=all neighbours (broadcast mode).
    def send_to_network(self, msg, devid, dest=None):
        time.sleep(0.01)
        if random.random() > self.robustness:
            return False
        if dest is not None:
            self.dev[dest].process_msg(msg)
        else:
            for n in self.simulated_layout.get_neighbours(devid):
                self.dev[n].process_msg(msg)
        return True
