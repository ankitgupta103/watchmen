import json
import asyncio
import random
import time
import constants

class Device:
    def __init__(self, devid, fcomm, ncomm):
        self.devid = devid
        self.neighbours_seen = []
        self.spath = []
        self.fcomm = fcomm
        self.ncomm = ncomm
        self.image_count = 0
        self.event_count = 0
        self.seen_messages = {}
    
    async def log(self, message):
        if self.fcomm and hasattr(self.fcomm, 'log_message'):
            await self.fcomm.log_message(f"Node {self.devid}: {message}")

    async def send_message(self, msg, dest=None):
        if msg is None: return False
        return await self.fcomm.send_to_network(msg, self.devid, dest)

    def get_next_on_spath(self):
        if not self.spath or len(self.spath) < 2 or self.spath[0] != self.devid:
            return None
        return self.spath[1]

    def make_hb_msg(self, ts):
        if not self.spath or len(self.spath) < 2: return None
        return {
            constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_HEARTBEAT,
            constants.JK_SOURCE: self.devid,
            constants.JK_SOURCE_TIMESTAMP: ts,
            constants.JK_NEIGHBOURS: self.neighbours_seen,
            constants.JK_IMAGE_COUNT: self.image_count,
            constants.JK_EVENT_COUNT: self.event_count,
            constants.JK_SHORTEST_PATH: self.spath,
            constants.JK_PATH_SO_FAR: [],
        }

    async def propagate_message(self, msg):
        """
        Propagates a message, trying the shortest path first and then falling
        back to other neighbors if the primary route fails.
        """
        if msg is None: 
            return

        path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
        primary_next_hop = self.get_next_on_spath()
        
        # 1. Attempt to send via the primary shortest path
        primary_send_success = False
        if primary_next_hop and primary_next_hop not in path_so_far:
            primary_msg = msg.copy()
            primary_msg[constants.JK_DEST] = primary_next_hop
            primary_msg[constants.JK_PATH_SO_FAR] = path_so_far + [self.devid]
            primary_msg[constants.JK_LAST_TS] = time.time_ns()
            
            await self.log(f"Propagating {primary_msg.get(constants.JK_MESSAGE_TYPE)} to primary hop {primary_next_hop}...")
            primary_send_success = await self.send_message(primary_msg, primary_next_hop)

        # 2. If primary send failed, attempt fallback routing
        if not primary_send_success:
            if primary_next_hop: # Log failure only if there was a primary hop to begin with
                await self.log(f"Primary hop {primary_next_hop} failed. Searching for fallback route...")
            
            # Iterate through other known neighbors to find a fallback
            for fallback_neighbour in self.neighbours_seen:
                # A valid fallback cannot be the failed primary hop or anyone already in the path
                if fallback_neighbour != primary_next_hop and fallback_neighbour not in path_so_far:
                    fallback_msg = msg.copy()
                    fallback_msg[constants.JK_DEST] = fallback_neighbour
                    fallback_msg[constants.JK_PATH_SO_FAR] = path_so_far + [self.devid]
                    fallback_msg[constants.JK_LAST_TS] = time.time_ns()

                    await self.log(f"Redirecting via fallback neighbor {fallback_neighbour}...")
                    fallback_send_success = await self.send_message(fallback_msg, fallback_neighbour)
                    
                    if fallback_send_success:
                        # Once we successfully send to one fallback neighbor, our job is done.
                        return # Exit the function
            
            # If we get here, all fallbacks also failed or no valid ones were found
            await self.log("No viable fallback neighbors found. Message propagation failed.")
        
    async def send_scan_message(self):
        await self.log("Scanning for neighbors...")
        scan_msg = {
            constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_SCAN,
            constants.JK_SOURCE: self.devid,
            constants.JK_SOURCE_TIMESTAMP: time.time_ns(),
        }
        await self.send_message(scan_msg)

    async def send_hb(self):
        ts = time.time_ns()
        msg = self.make_hb_msg(ts)
        if msg:
            await self.log(f"Sending heartbeat. Path: {'->'.join(self.spath)}")
            await self.propagate_message(msg)
        
    def process_msg(self, msg):
        mtype = msg.get(constants.JK_MESSAGE_TYPE)
        source = msg.get(constants.JK_SOURCE)
        
        msg_id = f"{msg.get(constants.JK_SOURCE)}-{msg.get(constants.JK_SOURCE_TIMESTAMP)}"
        if mtype != constants.MESSAGE_TYPE_SCAN:
            current_time = time.time()
            for seen_id, seen_time in list(self.seen_messages.items()):
                if current_time - seen_time > 10:
                    del self.seen_messages[seen_id]
            if msg_id in self.seen_messages:
                return
            self.seen_messages[msg_id] = current_time

        loop = asyncio.get_running_loop()

        if mtype == constants.MESSAGE_TYPE_SCAN:
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
                loop.create_task(self.log(f"Discovered neighbor {source}"))
        
        elif mtype == constants.MESSAGE_TYPE_SPATH:
            loop.create_task(self.spread_spath(msg))
            
        elif mtype in [constants.MESSAGE_TYPE_HEARTBEAT, constants.MESSAGE_TYPE_PHOTO]:
            loop.create_task(self.propagate_message(msg))
    
    async def spread_spath(self, msg):
        path_from_sender = msg.get(constants.JK_SHORTEST_PATH, [])
        source = msg.get(constants.JK_SOURCE)
        if not path_from_sender:
            return

        if path_from_sender[0] == self.devid:
            new_spath = path_from_sender
        else:
            new_spath = [self.devid] + path_from_sender
        
        is_new_or_shorter = not self.spath or len(new_spath) < len(self.spath)
        is_refresh_from_parent = self.spath and len(self.spath) > 1 and source == self.spath[1]

        if is_new_or_shorter or is_refresh_from_parent:
            self.spath = new_spath
            if is_new_or_shorter:
                await self.log(f"New shortest path: {'->'.join(self.spath)}")
            else:
                await self.log(f"Refreshed path: {'->'.join(self.spath)}")
            
            new_msg = {
                constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_SPATH,
                constants.JK_SOURCE: self.devid,
                constants.JK_SOURCE_TIMESTAMP: time.time_ns(),
                constants.JK_SHORTEST_PATH: self.spath
            }

            last_hop_in_path = path_from_sender[0]
            for neighbour in self.neighbours_seen:
                if neighbour != last_hop_in_path:
                    await self.send_message(new_msg.copy(), neighbour)