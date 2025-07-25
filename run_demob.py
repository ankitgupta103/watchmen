from datetime import datetime
import os
import sys
import time
import threading
import image
import json
import socket
import random
from lora_comm import RFComm
from vyom_client import VyomClient
from PIL import Image  # Import Pillow for image manipulation
import io  # For handling image bytes
import logging

# import gps
import constants

ALLDIR = "../processed_images"
CCDIR = "../command_images"
CRITICAL_DIR = "../processed_images/critical"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("run_demob.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_hostname():
    return socket.gethostname()


def is_node_cc(devid):
    if devid in constants.NEXT_DEST_MAP.keys():
        return False
    return True


def get_next_dest(devid):
    if devid in constants.NEXT_DEST_MAP:
        dest = constants.NEXT_DEST_MAP[devid]
        return dest
    logger.error(f"Error getting next dest for {devid}")
    return None


def get_files_in_dir(alldir, criticaldir):
    allfiles = []
    for a in os.listdir(alldir):
        allfiles.append(os.path.join(alldir, a))
    total_images_taken = len(allfiles)
    criticalfiles = []
    for c in os.listdir(criticaldir):
        criticalfiles.append(os.path.join(criticaldir, c))
    return (total_images_taken, criticalfiles)


def get_time_str():
    t = datetime.now()
    return f"{str(t.hour).zfill(2)}{str(t.minute).zfill(2)}"


# New function to downscale image if needed
def downscale_image_if_needed(image_path, target_kb=60, scale_percent=0.60):
    """
    Checks the image size. If it's larger than target_kb, downscales it by scale_percent.
    Returns the image data as bytes (potentially downscaled).
    """
    try:
        # Read image as bytes
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Get original size in KB
        original_size_kb = len(image_bytes) / 1024
        if original_size_kb > target_kb:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            new_width = int(width * scale_percent)
            new_height = int(height * scale_percent)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save the downscaled image to a bytes buffer
            img_byte_arr = io.BytesIO()
            # Determine format based on original file extension
            format = (
                img.format if img.format else "JPEG"
            )  # Default to JPEG if format is not detected
            img.save(img_byte_arr, format=format)
            downscaled_image_bytes = img_byte_arr.getvalue()
            return downscaled_image_bytes
        else:
            return image_bytes

    except Exception as e:
        logger.error(
            f"Error processing image {image_path} for downscaling: {e}", exc_info=True
        )
        # If an error occurs, return the original image bytes to avoid breaking the flow
        try:
            with open(image_path, "rb") as f:
                return f.read()
        except Exception as read_e:
            logger.error(
                f"Failed to read original image bytes after downscaling error: {read_e}"
            )
            return None


class CommandCenter:
    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        self.node_map = (
            {}
        )  # id->(num HB, last HB, gps, Num photos, Num events, [(Event TS, EventID)])
        self.images_saved = []
        self.msgids_seen = []
        self.vyom_client = VyomClient(logger=logger)
        self.logger = logger
        self._start_central_heartbeat()

    def _run_central_heartbeat(self):
        # Initial send on startup
        self.hb_central()
        while True:
            time.sleep(constants.HB_TIME_SEC)  # Send heartbeat every 1 minute
            self.hb_central()

    def _start_central_heartbeat(self):
        central_hb_thread = threading.Thread(
            target=self._run_central_heartbeat, daemon=True
        )
        central_hb_thread.start()

    def hb_central(self):
        """
        Sends heartbeat data for the central unit to the VyomClient.
        This function will be run in a separate thread, periodically.
        """
        # gpsgetter= gps.Gps()
        loc = None  # gpsgetter.get_lat_lng()

        lat = None
        long = None

        if (
            loc
            and loc[0] is not None
            and loc[1] is not None
            and loc[0] != 0
            and loc[1] != 0
        ):
            lat, long = loc
            self.logger.info(f"Central unit GPS obtained: Lat={lat}, Long={long}")
        else:
            self.logger.warning(
                "Could not obtain central unit GPS, using random Srinagar location."
            )
            # Random Srinagar locations for fallback
            srinagar_locations = [
                (34.083656, 74.797371),  # General Srinagar
                (34.1200, 74.8700),  # Dal Lake
                (34.1424, 74.8398),  # Nigeen Lake (approx)
                (34.1426, 74.8629),  # Shalimar Bagh (Srinagar)
                (34.098352, 74.809180),  # Jamia Masjid Srinagar
            ]
            lat, long = random.choice(srinagar_locations)
            self.logger.info(
                f"Using fallback Srinagar location: Lat={lat}, Long={long}"
            )

        try:
            self.vyom_client.on_central_unit_hb_arrive(lat=lat, long=long)
            self.logger.info(
                f"Central unit heartbeat sent to VyomClient: Lat={lat}, Long={long}"
            )
        except Exception as e:
            self.logger.error(
                f"Error sending central unit heartbeat to VyomClient: {e}",
                exc_info=True,
            )

    # A:1205:100:12
    def process_hb(self, hbstr):
        parts = hbstr.split(":")
        if len(parts) != 4:
            self.logger.error(f"Error parsing hb : {hbstr}")
            return
        nodeid = parts[0]
        hbtime = parts[1]
        photos_taken = int(parts[2])
        events_seen = int(parts[3])
        hbcount = 0
        gpsloc = ""
        eventtslist = []
        if nodeid not in self.node_map.keys():
            hbcount = 1
        else:
            (hbc, _, gpsloc, _, _, el) = self.node_map[nodeid]
            hbcount = hbc + 1
            eventtslist = el
        self.node_map[nodeid] = (
            hbcount,
            hbtime,
            gpsloc,
            photos_taken,
            events_seen,
            eventtslist,
        )
        # SENDING TO VYOM
        try:
            lat = None
            long = None
            if gpsloc is not None and gpsloc != "":
                try:
                    lat, long = gpsloc.split(",")
                    lat = float(lat)
                    long = float(long)
                except Exception as e:
                    self.logger.error(f"Error parsing gpsloc {e}, gpsloc={gpsloc}")
                    lat = None
                    long = None
            self.logger.info(
                f"Heartbeat received: node_hn={nodeid}, lat={lat}, long={long}"
            )
            self.vyom_client.on_hb_arrive(
                node_hn=nodeid, lat=lat, long=long, timestamp=hbtime
            )
            self.logger.info(
                f"Heartbeat sent to vyom client: node_hn={nodeid}, lat={lat}, long={long}"
            )
        except Exception as e:
            self.logger.error(
                f"Error sending hb to vyom client: node_hn={nodeid}, lat={lat}, long={long}, error={e}",
                exc_info=True,
            )

    def print_status(self):
        while True:
            self.logger.info("######### Command Center status ##############")
            for x in self.node_map.keys():
                self.logger.info(f"{x} : {self.node_map[x]}")
            for x in self.images_saved:
                self.logger.info(f"Saved image : {x}")
            self.logger.info("##############################################")
            time.sleep(10)

    def process_image(self, msgstr):
        try:
            orig_msg = json.loads(msgstr)
        except Exception as e:
            self.logger.error(f"Error loading json {e}")
        if "i_d" in orig_msg:
            imf = orig_msg["i_f"]
            ims = orig_msg["i_s"]
            imstr = orig_msg["i_d"]
            evid = orig_msg["e_i"]
            im = image.imstrtoimage(imstr)
            fname = f"{CCDIR}/{ims}_{random.randint(1000,2000)}_{imf}"
            self.logger.info(f"Image saved to {fname}")
            im.save(fname)
            self.images_saved.append(fname)
            # SENDING TO VYOM
            try:
                imf = orig_msg["i_f"]
                file_name_suffix = imf.split("_")[-1].split(".")[0]
                filename = f"{evid}_{file_name_suffix}.jpg"
                image_bytes = image.imstrtobytes(imstr)
                self.logger.info(
                    f"Image sent to vyom client: node_hn={ims}, filename={filename}"
                )
                self.vyom_client.on_image_arrive(
                    node_hn=ims, image=image_bytes, filename=filename
                )
            except Exception as e:
                self.logger.error(
                    f"Error sending image to vyom client: node_hn={ims}, filename={filename}, error={e}",
                    exc_info=True,
                )

    # A:1205
    def process_event(self, eventstr):
        parts = eventstr.split(":")
        if len(parts) != 4:
            self.logger.error(f"Error parsing event message : {eventstr}")
            return
        nodeid = parts[0]
        eventtime = parts[1]
        evid = parts[2]
        event_severity = parts[3]
        if nodeid not in self.node_map:
            self.node_map[nodeid] = (0, "", "", 1, 1, [])
            self.logger.warning(f"Node {nodeid} not in map yet (event before HB)")
        (hbcount, hbtime, gpsloc, photos_taken, events_seen, event_ts_list) = (
            self.node_map[nodeid]
        )
        event_ts_list.append((eventtime, evid))
        self.node_map[nodeid] = (
            hbcount,
            hbtime,
            gpsloc,
            photos_taken,
            events_seen,
            event_ts_list,
        )

        meta = {
            "node_id": nodeid,
            "hb_count": hbcount,
            "last_hb_time": hbtime,
            "photos_taken": photos_taken,
            "events_seen": events_seen,
        }

        # SENDING TO VYOM
        try:
            self.logger.info(
                f"Event sent to vyom client: node_hn={nodeid}, event_id={evid}, severity={event_severity}"
            )
            self.vyom_client.on_event_arrive(
                node_hn=nodeid,
                event_id=evid,
                eventstr=eventstr,
                event_severity=event_severity,
                meta=meta,
            )
        except Exception as e:
            self.logger.error(
                f"Error sending event to vyom client: node_hn={nodeid}, event_id={evid}, error={e}",
                exc_info=True,
            )

    def process_gps(self, msgstr):
        parts = msgstr.split(":")
        if len(parts) != 2:
            self.logger.error(f"Error parsing event message : {msgstr}")
            return
        nodeid = parts[0]
        gpsloc = parts[1]
        if nodeid not in self.node_map:
            self.node_map[nodeid] = (0, "", gpsloc, 0, 0, [])
        (hbcount, hbtime, _, photos_taken, events_seen, event_ts_list) = self.node_map[
            nodeid
        ]
        self.node_map[nodeid] = (
            hbcount,
            hbtime,
            gpsloc,
            photos_taken,
            events_seen,
            event_ts_list,
        )

    def process_msg(self, msgid, mst, msgstr):
        if msgid not in self.msgids_seen:
            self.msgids_seen.append(msgid)
        else:
            return
        if mst == constants.MESSAGE_TYPE_PHOTO:
            self.logger.info(f"Image received at command center")
            self.process_image(msgstr)
        elif mst == constants.MESSAGE_TYPE_HEARTBEAT:
            self.logger.info(f"Heartbeat received at command center")
            self.process_hb(msgstr)
        elif mst == constants.MESSAGE_TYPE_EVENT:
            self.logger.info(f"Event received at command center")
            self.process_event(msgstr)
        elif mst == constants.MESSAGE_TYPE_GPS:
            self.logger.info(f"GPS received at command center")
            self.process_gps(msgstr)
        return True


class DevUnit:
    msg_queue = []  # str, type, dest tuple list
    msg_queue_lock = threading.Lock()

    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        self.keep_propagating()
        self.msgids_seen = []
        self.photos_taken = 0
        self.critical_images_processed = []
        self.critical_images_sent = []
        self.logger = logger

    def process_msg(self, msgid, mst, msgstr):
        if msgid not in self.msgids_seen:
            self.msgids_seen.append(msgid)
        else:
            return
        next_dest = get_next_dest(self.devid)
        if next_dest:
            if next_dest == None:
                self.logger.warning(f"{self.devid} Weird no dest for {self.devid}")
                return
            with self.msg_queue_lock:
                self.msg_queue.append((msgstr, mst, next_dest))
        else:
            self.logger.warning(f"{self.devid}: Has no Dest, this should never happen")

    def get_images_to_send(self, critical_images):
        cropped = None
        full = None
        immap = {}  # Evid to list of images for that event.
        new_images = []
        event_severity = None  # Initialize to None to avoid UnboundLocalError
        for f in critical_images:
            if f not in self.critical_images_processed:
                self.critical_images_processed.append(f)
                new_images.append(f)
        for f in new_images:
            fname = f.split("/").pop()
            event_severity = fname.split("_")[
                0
            ]  # Set event_severity here for each new image
            evid = fname.split("_")[2]
            if evid not in immap:
                immap[evid] = [f]
            else:
                immap[evid].append(f)
        latest_ts = "0"
        latest_full_evid = None
        for evid in immap:
            if len(immap[evid]) != 2:
                logger.error(f"{evid} doesnt have 2 images : {immap[evid]}")
                continue
            for f in immap[evid]:
                fname = f.split("/").pop()
                ts = fname.split("_")[1]
                if ts > latest_ts or latest_full_evid is None:
                    latest_ts = ts
                    latest_full_evid = evid
                    # Set event_severity from the filename of the latest image
                    event_severity = fname.split("_")[0]
        if latest_full_evid is not None:
            logger.info(
                f"Sending images for event {latest_full_evid}: {immap[latest_full_evid]}"
            )
            if len(immap[latest_full_evid]) == 2:
                for f in immap[latest_full_evid]:
                    fname = f.split("/").pop()
                    if f.find("_f.jpg") > 0:
                        full = f
                    elif f.find("_c.jpg") > 0:
                        cropped = f
        return (latest_full_evid, cropped, full, event_severity)

    # def send_img(self, imgfile, evid):
    #     next_dest = get_next_dest(self.devid)
    #     self.logger.info(f"Sending image {imgfile} to {next_dest}")
    #     if next_dest == None:
    #         self.logger.warning(f"{self.devid} Weird no dest for {self.devid}")
    #         return
    #     mst = constants.MESSAGE_TYPE_PHOTO
    #     fname = imgfile.split("/").pop()
    #     im = {"i_f" : fname,
    #           "i_s" : self.devid,
    #           "i_t" : str(int(time.time())),
    #           "e_i" : evid,
    #           "i_d" : image.image2string(imgfile)}
    #     msgstr = json.dumps(im)
    #     self.rf.send_message(msgstr, mst, next_dest)

    def send_img(self, imgfile, evid):
        next_dest = get_next_dest(self.devid)
        self.logger.info(f"Sending image {imgfile} to {next_dest}")
        if next_dest == None:
            self.logger.warning(f"{self.devid} Weird no dest for {self.devid}")
            return

        # Downscale image if necessary
        processed_image_bytes = downscale_image_if_needed(imgfile)
        if processed_image_bytes is None:
            self.logger.error(
                f"Failed to process image {imgfile} for sending. Skipping."
            )
            return

        mst = constants.MESSAGE_TYPE_PHOTO
        fname = imgfile.split("/").pop()

        # Use image.imagebytes2string to convert the processed bytes to a string
        imstr = image.imagebytes2string(processed_image_bytes)

        im = {
            "i_f": fname,
            "i_s": self.devid,
            "i_t": str(int(time.time())),
            "e_i": evid,
            "i_d": imstr,
        }  # Use the potentially downscaled image string
        msgstr = json.dumps(im)
        self.rf.send_message(msgstr, mst, next_dest)

    def _keep_propagating(self):
        while True:
            to_send = False
            msgstr = None
            mst = ""
            dest = ""
            with self.msg_queue_lock:
                if len(self.msg_queue) > 0:
                    (msgstr, mst, dest) = self.msg_queue.pop(0)
                    to_send = True
            if to_send:
                self.logger.info(f"Propagating message {mst} to {dest}")
                self.rf.send_message(msgstr, mst, dest)
            time.sleep(0.5)

    # Non blocking, background thread
    def keep_propagating(self):
        # Start background thread to read incoming data
        propogation_thread = threading.Thread(
            target=self._keep_propagating, daemon=True
        )
        propogation_thread.start()

    def _keep_beating_heart(self):
        # self.send_gps() # Temporatily turning off gps
        while True:
            self.send_heartbeat(self.photos_taken, len(self.critical_images_processed))
            time.sleep(constants.HB_TIME_SEC)  # Every 1 min

    # Non blocking, background thread
    def keep_beating_heart(self):
        hb_thread = threading.Thread(target=self._keep_beating_heart, daemon=True)
        hb_thread.start()

    def keep_sending_to_cc(self):
        self.keep_beating_heart()
        photos_seen = 0
        events_seen = 0
        while True:
            time.sleep(10)
            (photos_seen, critical_images) = get_files_in_dir(ALLDIR, CRITICAL_DIR)
            self.photos_taken = photos_seen
            if len(critical_images) > 0:
                (evid, cropped, full, event_severity) = self.get_images_to_send(
                    critical_images
                )
                if cropped or full:
                    self.logger.info(
                        f"Found new critical images, sending : {cropped}, {full}"
                    )
                    events_seen += 1
                    self.send_event(evid, event_severity)
                    time.sleep(2)
                if cropped:
                    self.send_img(cropped, evid)
                    time.sleep(40)
                if full:
                    self.send_img(full, evid)
                    time.sleep(60)

    # A:1205:100:12
    # Name, time, images taken, events noticed.
    def send_heartbeat(self, photos_taken, events_seen):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}:{photos_taken}:{events_seen}"
        next_dest = get_next_dest(self.devid)
        self.rf.send_message(msgstr, constants.MESSAGE_TYPE_HEARTBEAT, next_dest)

    # A:23.1,67.1
    # Name:GPS
    def send_gps(self):
        gpsgetter = gps.Gps()
        loc = gpsgetter.get_lat_lng()
        if loc is not None:
            (lat, lng) = loc
            next_dest = get_next_dest(self.devid)
            msgstr = f"{self.devid}:{lat},{lng}"
            self.rf.send_message(msgstr, constants.MESSAGE_TYPE_GPS, next_dest)

    # A:1205
    # Name, time
    def send_event(self, evid, event_severity):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}:{evid}:{event_severity}"
        self.logger.info(f"Sending event id : {msgstr}")
        next_dest = get_next_dest(self.devid)
        self.rf.send_message(msgstr, constants.MESSAGE_TYPE_EVENT, next_dest, True)


def run_unit():
    hname = get_hostname()
    if hname not in constants.HN_ID:
        return None
    devid = constants.HN_ID[hname]
    logger.info(f"Running as host {hname} and devid {devid}")
    if is_node_cc(devid):
        cc = CommandCenter(devid)
        cc.print_status()
    else:
        du = DevUnit(devid)
        du.keep_sending_to_cc()
    time.sleep(10000000)


def main():
    run_unit()


if __name__ == "__main__":
    main()
