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

    def add_flakiness(self, msg, devid):
        # return False # Disable flakiness for now
        # Flakiness in node. 2-3 Nodes should fail sending and receiving messages and see the network recover.
        r = random.random()
        if devid in ["VVV", "NNN", "CCC"]:
            if r < 0.4:
                print(f"Flaky network failing to send for {devid} msg type = {msg['message_type']}")
                return True
        if devid in ["QQQ"]:
            if msg["message_type"] == constants.MESSAGE_TYPE_HEARTBEAT:
                return True

    # Send msg of mtype to dest, None=all neighbours (broadcast mode).
    def send_to_network(self, msg, devid, dest=None):
        time.sleep(0.01)
        if self.add_flakiness(msg, devid):
            return False
        if dest is not None:
            self.dev[dest].process_msg(msg)
        else:
            for n in self.simulated_layout.get_neighbours(devid):
                self.dev[n].process_msg(msg)
        return True
