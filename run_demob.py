from datetime import datetime
import sys
import time
import threading
import image
import json
import socket
import random
import os
import glob
from pathlib import Path
from rf_comm import RFComm

import constants
from detect_enhanced import Detector  # Using enhanced detector
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson

def get_hostname():
    return socket.gethostname()

def is_node_src(devid):
    return constants.PATH_DEMOB[0] == devid

def is_node_dest(devid):
    return constants.PATH_DEMOB[-1] == devid

def is_node_passthrough(devid):
    if is_node_src(devid) or is_node_dest(devid):
        return False
    return True

def get_next_dest(devid):
    idx = -1
    num_nodes = len(constants.PATH_DEMOB)
    for i in range(num_nodes):
        if devid == constants.PATH_DEMOB[i]:
            if i + 1 >= num_nodes:
                return None
            else:
                return constants.PATH_DEMOB[i+1]
    return None

def get_time_str():
    t = datetime.now()
    return f"{str(t.hour).zfill(2)}{str(t.minute).zfill(2)}"

def get_severity_from_detection(detected_objects, confidence_scores):
    """Determine message severity based on detection results"""
    if not detected_objects:
        return "low"
    
    max_confidence = max(confidence_scores) if confidence_scores else 0
    
    # Check for high-risk items
    high_risk_items = ["knife", "scissors", "gun", "baseball bat"]
    medium_risk_items = ["person", "backpack", "handbag", "suitcase"]
    
    for obj in detected_objects:
        if obj in high_risk_items:
            return "critical" if max_confidence > 0.8 else "high"
        elif obj in medium_risk_items:
            return "high" if max_confidence > 0.7 else "medium"
    
    return "medium" if max_confidence > 0.5 else "low"

class CommandCenter:
    def __init__(self, devid):
        self.devid = devid
        # self.rf = RFComm(devid)
        # self.rf.add_node(self)
        # self.rf.keep_reading()
        self.node_map = {} # id->(num HB, last HB, Num photos, Num events, [Event TS])
        self.images_saved = []
        self.msgids_seen = []
        
        self.writer = QueueWriterJson()
        self.mission_id = "_all_"
        print(f"Command Center {devid} initialized with vyomcloudbridge writer")

    def publish_health_event(self, machine_id, event_type="unknown", severity="low", details=""):
        """Publish health event data to cloud"""
        try:
            epoch_ms = int(time.time() * 1000)
            message_data = {
                "timestamp": datetime.now().isoformat(),
                "machine_id": machine_id,
                "type": event_type,
                "severity": severity,
                "details": details
            }
            
            filename = f"health_{machine_id}_{epoch_ms}.json"
            
            self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-health",
                data_type="json",
                mission_id=self.mission_id,
                priority=1,
                destination_ids=["s3"]
            )
            
            print(f"Health event published for machine {machine_id}: {event_type} ({severity})")
                
        except Exception as e:
            print(f"Error publishing health event for {machine_id}: {e}")

    def publish_suspicious_event(self, machine_id, image_base64, confidence=0.85, event_type="unknown", detected_objects=None):
        """Publish suspicious event data to cloud"""
        try:
            epoch_ms = int(time.time() * 1000)
            
            # Determine severity based on detected objects
            confidences = [confidence] if isinstance(confidence, float) else confidence
            severity = get_severity_from_detection(detected_objects or [], confidences)
            
            message_data = {
                "machine_id": machine_id,
                "timestamp": datetime.now().isoformat(),
                "url": image_base64,  # Image as base64
                "confidence": confidence,
                "type": event_type,
                "severity": severity,
                "detected_objects": detected_objects or [],
                "details": {
                    "detection_count": len(detected_objects) if detected_objects else 0,
                    "max_confidence": max(confidences) if confidences else 0
                }
            }
            
            filename = f"suspicious_{machine_id}_{epoch_ms}.json"
            
            priority = 3 if severity in ["high", "critical"] else 2
            
            self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-suspicious",
                data_type="json",
                mission_id=self.mission_id,
                priority=priority,
                destination_ids=["s3"]
            )
            
            print(f"Suspicious event published for machine {machine_id}: {event_type} ({severity}) - confidence: {confidence}")
                
        except Exception as e:
            print(f"Error publishing suspicious event for {machine_id}: {e}")

    def publish_summary(self):
        """Publish network summary"""
        try:
            epoch_ms = int(time.time() * 1000)
            
            total_nodes = len(self.node_map)
            total_images = len(self.images_saved)
            
            message_data = {
                "timestamp": datetime.now().isoformat(),
                "machine_id": self.devid,
                "total_nodes": total_nodes,
                "total_images": total_images,
                "active_nodes": list(self.node_map.keys())
            }
            
            filename = f"summary_{epoch_ms}.json"
            
            self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-summary",
                data_type="json",
                mission_id=self.mission_id,
                priority=1,
                destination_ids=["s3"]
            )
            
            print(f"Summary published successfully")
                
        except Exception as e:
            print(f"Error publishing summary: {e}")

    def print_status(self):
        status_count = 0
        while True:
            print("######### Command Center printing status ##############")
            for x in self.node_map.keys():
                print(f" ####### {x} : {self.node_map[x]}")
            for x in self.images_saved:
                print(f"Saved image : {x}")
            print("#######################################################")
            
            # Publish summary every 10 status updates (every 100 seconds)
            status_count += 1
            if status_count % 10 == 0:
                self.publish_summary()
            
            time.sleep(10)

    def process_image(self, msgstr):
        try:
            orig_msg = json.loads(msgstr)
        except Exception as e:
            print(f"Error loading json {e}")
            return
            
        print("Checking for image")
        if "i_d" in orig_msg:
            print("Seems like an image")
            imstr = orig_msg["i_d"]
            im = image.imstrtoimage(imstr)
            fname = f"/tmp/commandcenter_{random.randint(1000,2000)}.jpg"
            print(f"Saving image to {fname}")
            im.save(fname)
            self.images_saved.append(fname)
            
            # Extract detection results from message
            source_node = orig_msg.get("i_s", "unknown")
            image_base64 = orig_msg.get("i_d", "") 
            detected_objects = orig_msg.get("detected_objects", [])
            confidence = orig_msg.get("confidence", 0.85)
            detection_type = orig_msg.get("detection_type", "unknown")
            
            self.publish_suspicious_event(
                source_node, 
                image_base64, 
                confidence, 
                detection_type, 
                detected_objects
            )

    def process_hb(self, hbstr):
        parts = hbstr.split(':')
        if len(parts) != 4:
            print(f"Error parsing hb : {hbstr}")
            return
        nodeid = parts[0]
        hbtime = parts[1]
        photos_taken = int(parts[2])
        events_seen = int(parts[3])
        hbcount = 0
        eventtslist = []
        if nodeid not in self.node_map.keys():
            hbcount = 1
        else:
            (hbc, _, _, _, el) = self.node_map[nodeid]
            hbcount = hbc + 1
            eventtslist = el
        self.node_map[nodeid] = (hbcount, hbtime, photos_taken, events_seen, eventtslist)
        
        # Publish health event - device is alive and reporting
        self.publish_health_event(nodeid, "heartbeat", "low", f"Device reporting - photos: {photos_taken}, events: {events_seen}")
    
    def process_event(self, eventstr):
        parts = eventstr.split(':')
        if len(parts) != 2:
            print(f"Error parsing event message : {eventstr}")
            return
        nodeid = parts[0]
        eventtime = parts[1]
        if nodeid not in self.node_map:
            print(f"Weird that node {nodeid} not in map yet")
            return
        (hbcount, hbtime, photos_taken, events_seen, event_ts_list) = self.node_map[nodeid]
        event_ts_list.append(eventtime)
        self.node_map[nodeid] = (hbcount, hbtime, photos_taken, events_seen, event_ts_list)
        
        # Publish health event for device activity
        self.publish_health_event(nodeid, "device_activity", "low", f"Event reported at {eventtime}")

    def process_msg(self, msgid, mst, msgstr):
        if msgid not in self.msgids_seen:
            self.msgids_seen.append(msgid)
        else:
            print(f"Skipping message id : {msgid}")
            return
        if mst == constants.MESSAGE_TYPE_PHOTO:
            print(f"########## Image received at command center")
            self.process_image(msgstr)
        elif mst == constants.MESSAGE_TYPE_HEARTBEAT:
            print(f"########## Message received at command center : {mst} : {msgstr}")
            self.process_hb(msgstr)
        elif mst == constants.MESSAGE_TYPE_EVENT:
            print(f"########## Message received at command center : {mst} : {msgstr}")
            self.process_event(msgstr)
        return True

class DevUnit:
    msg_queue = [] # str, type, dest tuple list
    msg_queue_lock = threading.Lock()

    def __init__(self, devid):
        self.devid = devid
        # self.rf = RFComm(devid)
        # self.rf.add_node(self)
        # self.rf.keep_reading()
        self.keep_propagating()
        self.msgids_seen = []
        
        # Initialize enhanced detector
        self.detector = Detector()
        self.detector.set_detection_category("all")  # Detect all objects
        
        # Image processing settings
        self.image_directory = "/home/pi/Documents/images"
        self.processed_images = set()  # Track processed images
        self.images_processed = 0
        self.events_detected = 0
       
    def process_msg(self, msgid, mst, msgstr):
        if msgid not in self.msgids_seen:
            self.msgids_seen.append(msgid)
        else:
            print(f"Skipping message id : {msgid}")
            return
        if is_node_passthrough(self.devid):
            next_dest = get_next_dest(self.devid)
            if next_dest == None:
                print(f"{self.devid} Weird no dest for {self.devid}")
                return
            print(f"In Passthrough mode, trying to acquire lock")
            with self.msg_queue_lock:
                print(f"{self.devid} Adding message to send queue for {next_dest}")
                self.msg_queue.append((msgstr, mst, next_dest))
        if is_node_src(self.devid):
            print(f"{self.devid}: Src should not be getting any messages")

    def get_image_files(self):
        """Get all image files from the specified directory"""
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.tiff']
        image_files = []
        
        if not os.path.exists(self.image_directory):
            print(f"Warning: Image directory {self.image_directory} does not exist")
            return []
        
        for extension in image_extensions:
            pattern = os.path.join(self.image_directory, '**', extension)
            image_files.extend(glob.glob(pattern, recursive=True))
            
        return sorted(image_files)

    def process_image_with_enhanced_detector(self, image_path):
        """Process image with enhanced detector and return results"""
        try:
            print(f"Processing image: {image_path}")
            
            # Run detection
            has_objects = self.detector.ImageHasTargetObjects(image_path, crop_objects=True)
            
            if has_objects:
                # Get cropped object files (they're saved in the same directory with modified names)
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                crop_pattern = f"{base_name}_*_cropped.jpg"
                crop_dir = os.path.dirname(image_path)
                cropped_files = glob.glob(os.path.join(crop_dir, crop_pattern))
                
                return {
                    "has_detection": True,
                    "cropped_files": cropped_files,
                    "original_file": image_path
                }
            else:
                return {
                    "has_detection": False,
                    "cropped_files": [],
                    "original_file": image_path
                }
                
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            return {
                "has_detection": False,
                "cropped_files": [],
                "original_file": image_path,
                "error": str(e)
            }

    def send_processed_images(self, detection_result):
        """Send cropped images first, then original image"""
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        
        try:
            # First, send cropped images if any detections
            for cropped_file in detection_result["cropped_files"]:
                self.send_img(cropped_file, is_cropped=True, detection_result=detection_result)
                time.sleep(2)  # Small delay between sends
            
            # Then send original image
            self.send_img(detection_result["original_file"], is_cropped=False, detection_result=detection_result)
            
        except Exception as e:
            print(f"Error sending images: {e}")

    def send_img(self, imgfile, is_cropped=False, detection_result=None):
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        
        mst = constants.MESSAGE_TYPE_PHOTO
        
        # Extract detection information from filename if cropped
        detected_objects = []
        confidence = 0.85
        detection_type = "unknown"
        
        if is_cropped and detection_result:
            # Parse object type from cropped filename
            filename = os.path.basename(imgfile)
            if "_cropped.jpg" in filename:
                parts = filename.replace("_cropped.jpg", "").split("_")
                if len(parts) >= 3:
                    detected_objects = [parts[-2]]  # Object type
                    try:
                        confidence = float(parts[-1].replace("conf", ""))
                    except:
                        confidence = 0.85
                    detection_type = detected_objects[0] if detected_objects else "unknown"
        elif detection_result and detection_result["has_detection"]:
            detection_type = "multiple_objects"
            detected_objects = ["person"]  # Default, could be enhanced to track actual objects
        
        im = {
            "i_m": f"Image from {self.devid}",
            "i_s": self.devid,
            "i_t": str(int(time.time())),
            "i_d": image.image2string(imgfile),
            "is_cropped": is_cropped,
            "detected_objects": detected_objects,
            "confidence": confidence,
            "detection_type": detection_type,
            "has_detection": detection_result["has_detection"] if detection_result else False
        }
        
        msgstr = json.dumps(im)
        print(f"Sending {'cropped' if is_cropped else 'original'} image: {imgfile} (detection: {detection_type})")
        # self.rf.send_message(msgstr, mst, next_dest)

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
                print(f"Propagating message {mst} to {dest}")
                # self.rf.send_message(msgstr, mst, dest)
            time.sleep(0.5)

    def keep_propagating(self):
        propogation_thread = threading.Thread(target=self._keep_propagating, daemon=True)
        propogation_thread.start()

    def process_images_from_directory(self):
        """Process all images from the directory one by one"""
        image_files = self.get_image_files()
        
        if not image_files:
            print(f"No images found in {self.image_directory}")
            return
        
        print(f"Found {len(image_files)} images to process")
        
        for image_file in image_files:
            if image_file in self.processed_images:
                continue  # Skip already processed images
                
            print(f"\n{'='*50}")
            print(f"Processing image {len(self.processed_images) + 1}/{len(image_files)}: {os.path.basename(image_file)}")
            print(f"{'='*50}")
            
            # Process with enhanced detector
            detection_result = self.process_image_with_enhanced_detector(image_file)
            
            if detection_result["has_detection"]:
                print(f"Detection found! Cropped files: {len(detection_result['cropped_files'])}")
                self.events_detected += 1
                self.send_event()  # Send event notification
                time.sleep(2)
                
                # Send processed images (cropped first, then original)
                self.send_processed_images(detection_result)
            else:
                print("No detections found")
                # Still send original image for monitoring
                self.send_img(image_file, is_cropped=False, detection_result=detection_result)
            
            self.processed_images.add(image_file)
            self.images_processed += 1
            
            # Send heartbeat after processing each image
            time.sleep(5)
            self.send_heartbeat(self.images_processed, self.events_detected)
            
            # Wait before processing next image
            time.sleep(10)

    def keep_sending_to_cc(self, has_camera):
        photos_taken = 0
        events_seen = 0
        
        # Initial heartbeat
        self.send_heartbeat(photos_taken, events_seen)
        time.sleep(5)
        
        if has_camera:
            # Process images from directory
            self.process_images_from_directory()
        else:
            # Original behavior for non-camera devices
            while True:
                self.send_heartbeat(photos_taken, events_seen)
                time.sleep(1800)  # Every 30 mins

    def send_heartbeat(self, photos_taken, events_seen):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}:{photos_taken}:{events_seen}"
        next_dest = get_next_dest(self.devid)
        # self.rf.send_message(msgstr, constants.MESSAGE_TYPE_HEARTBEAT, next_dest)

    def send_gps(self):
        next_dest = get_next_dest(self.devid)
        msgstr = f"{self.devid}:28.4:77.0"
        # self.rf.send_message(msgstr, constants.MESSAGE_TYPE_GPS, next_dest)

    def send_event(self):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}"
        next_dest = get_next_dest(self.devid)
        # self.rf.send_message(msgstr, constants.MESSAGE_TYPE_EVENT, next_dest)

def run_unit():
    hname = get_hostname()
    if hname not in constants.HN_ID:
        print(f"Hostname {hname} not found in constants.HN_ID")
        print(f"Available hostnames: {list(constants.HN_ID.keys())}")
        return None
        
    devid = constants.HN_ID[hname]
    print(f"Device ID: {devid}, Hostname: {hname}")
    
    if is_node_dest(devid):
        print(f"Running as Command Center")
        cc = CommandCenter(devid)
        cc.print_status()
    else:
        print(f"Running as Device Unit")
        du = DevUnit(devid)
        has_camera = False
        if len(sys.argv) > 1:
            has_camera = sys.argv[1] == "c"
        print(f"Camera enabled: {has_camera}")
        du.keep_sending_to_cc(has_camera)
    
    time.sleep(10000000)

def main():
    try:
        run_unit()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__=="__main__":
    main()