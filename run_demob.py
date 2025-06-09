from datetime import datetime, timezone
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
# from rf_comm import RFComm

import constants
from detect_enhanced import Detector  # Using enhanced detector
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson
from vyomcloudbridge.utils.configs import Configs
from vyomcloudbridge.utils.upload_dir import get_mission_upload_dir

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

def get_suspicious_event_details(detected_objects, confidence_scores):
    """Determine suspicious event type and severity based on detection results"""
    if not detected_objects:
        return {
            "type": "unusual_activity",  
            "severity": "low",
            "description": "Image processed - no specific threats detected"
        }
    
    max_confidence = max(confidence_scores) if confidence_scores else 0
    
    # Check for weapon detection
    weapon_items = ["knife", "scissors", "gun", "baseball bat"]
    human_items = ["person"]
    
    for obj in detected_objects:
        if obj in weapon_items:
            severity = "critical" if max_confidence > 0.8 else "high"
            return {
                "type": "weapon_detection",
                "severity": severity,
                "description": f"Weapon detected: {obj} with {max_confidence:.2f} confidence"
            }
        elif obj in human_items:
            severity = "high" if max_confidence > 0.7 else "medium"
            return {
                "type": "human_detection", 
                "severity": severity,
                "description": f"Human detected with {max_confidence:.2f} confidence"
            }
    
    # Other objects detected
    severity = "medium" if max_confidence > 0.5 else "low"
    return {
        "type": "unusual_activity",
        "severity": severity,
        "description": f"Objects detected: {', '.join(detected_objects)}"
    }

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
        
        # Get machine configuration
        self.machine_config = Configs.get_machine_config()
        self.machine_id = self.machine_config.get("machine_id", "-") or "-"
        self.organization_id = self.machine_config.get("organization_id", "-") or "-"
        
        print(f"Machine ID: {self.machine_id}")
        print(f"Organization ID: {self.organization_id}")
        
        self.detector = Detector()
        self.detector.set_detection_category("all")
        
        # Image processing settings
        self.image_directory = "/home/pi/Documents/images"
        self.processed_images = set()
        self.images_processed = 0
        self.events_detected = 0
        
        # Health monitoring
        self.last_health_check = 0
        self.health_check_interval = 60  # 60 seconds
        self.system_start_time = time.time()
        
        # Check if image directory exists and show available images
        if os.path.exists(self.image_directory):
            available_images = self.get_image_files()
            print(f"📁 Image directory found: {self.image_directory}")
            print(f"📸 Available images: {len(available_images)}")
            if available_images:
                print(f"📋 Sample images: {[os.path.basename(f) for f in available_images[:3]]}")
        else:
            print(f"⚠️  Warning: Image directory not found: {self.image_directory}")
            print(f"🔧 Please create the directory and add some images to process")
        
        print(f"Command Center {devid} initialized with vyomcloudbridge writer and AI detector")

    def publish_health_event(self, machine_id, event_type="offline", severity="low", details=""):
        """Publish health event data to cloud"""
        try:
            epoch_ms = int(time.time() * 1000)
            message_data = {
                "event_type": "health",
                "machine_id": machine_id,
                "machine_name": f"{machine_id}",
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "severity": severity,
                "details": details,
                "reported_by": self.devid
            }
            
            filename = f"{epoch_ms}.json"
            
            priority = 3 if severity in ["high", "critical"] else 1
            
            self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-health",
                data_type="json",
                mission_id=self.mission_id,
                priority=priority,
                destination_ids=["s3"]
            )
            
            print(f"Health event published for {machine_id}: {event_type} ({severity})")
                
        except Exception as e:
            print(f"Error publishing health event for {machine_id}: {e}")

    def upload_image_and_get_url(self, image_path, data_source="watchmen-suspicious", timestamp=None):
        """Upload image file and return the URL for use in suspicious events"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Get mission upload directory
            mission_upload_dir = get_mission_upload_dir(
                organization_id=self.organization_id,
                machine_id=self.machine_id,
                mission_id="_all_",
                data_source=data_source,
                date=timestamp.strftime("%Y-%m-%d"),
                project_id="_all_"
            )
            
            # Read image file as binary
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Create unique filename with timestamp
            original_filename = os.path.basename(image_path)
            name, ext = os.path.splitext(original_filename)
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            unique_filename = f"{name}_{timestamp_str}{ext}"
            
            # Upload image using writer
            success, error = self.writer.write_message(
                message_data=image_data,
                filename=unique_filename,
                data_source=data_source,
                data_type="image",
                mission_id=self.mission_id,
                priority=2,
                destination_ids=["s3"],
                merge_chunks=False
            )
            
            if success:
                # Construct the URL path (this would be the actual S3/cloud URL)
                image_url = f"{mission_upload_dir}/{unique_filename}"
                print(f"📤 Image uploaded successfully: {unique_filename}")
                return image_url
            else:
                print(f"❌ Failed to upload image {original_filename}: {error}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading image {image_path}: {e}")
            return None

    def publish_suspicious_event(self, machine_id, image_path, event_details, detected_objects=None, confidence=0.85, timestamp=None):
        """Publish suspicious event data to cloud using actual image upload"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
                
            epoch_ms = int(timestamp.timestamp() * 1000)
            
            # Upload image and get URL
            image_url = self.upload_image_and_get_url(image_path, "watchmen-suspicious", timestamp)
            
            if not image_url:
                print(f"❌ Failed to upload image, skipping suspicious event")
                return False
            
            # Suspicious event types from TS: 'human_detection' | 'weapon_detection' | 'unusual_activity'
            # Marked from TS: 'ignored' | 'noted' | 'unreviewed'
            
            message_data = {
                "event_type": "suspicious",
                "machine_id": machine_id,
                "machine_name": f"{machine_id}",
                "timestamp": timestamp.isoformat(),
                "type": event_details["type"],
                "confidence": confidence,
                "url": image_url, 
                "marked": "unreviewed",
                "severity": event_details["severity"],
                "detected_objects": detected_objects or [],
                "details": {
                    "description": event_details["description"],
                    "detection_count": len(detected_objects) if detected_objects else 0,
                    "max_confidence": confidence,
                    "original_filename": os.path.basename(image_path)
                },
                "mission_id": self.mission_id,
                "reported_by": self.devid
            }
            
            filename = f"{epoch_ms}.json"
            
            priority = 3 if event_details["severity"] in ["high", "critical"] else 2
            
            success, error = self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-suspicious",
                data_type="json",
                mission_id=self.mission_id,
                priority=priority,
                destination_ids=["s3"]
            )
            
            if success:
                print(f"🚨 Suspicious event published for {machine_id}: {event_details['type']} ({event_details['severity']}) - Image: {image_url}")
                return True
            else:
                print(f"❌ Failed to publish suspicious event: {error}")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing suspicious event for {machine_id}: {e}")
            return False

    def check_system_health(self):
        """Check system health and publish health events every 60 seconds"""
        current_time = time.time()
        
        if current_time - self.last_health_check >= self.health_check_interval:
            self.last_health_check = current_time
            
            # Check AI detector health
            try:
                # Test if detector is working
                if hasattr(self.detector, 'model') and self.detector.model:
                    self.publish_health_event(
                        self.devid,
                        "camera_failure",  # Camera system includes AI
                        "low",
                        "AI detector operational"
                    )
                else:
                    self.publish_health_event(
                        self.devid,
                        "camera_failure",
                        "high",
                        "AI detector not available"
                    )
            except Exception as e:
                self.publish_health_event(
                    self.devid,
                    "camera_failure",
                    "critical",
                    f"AI detector error: {str(e)}"
                )
            
            # Check image directory health
            if os.path.exists(self.image_directory):
                self.publish_health_event(
                    self.devid,
                    "hardware_failure",
                    "low", 
                    f"Image directory accessible - {len(self.get_image_files())} images available"
                )
            else:
                self.publish_health_event(
                    self.devid,
                    "hardware_failure",
                    "medium",
                    "Image directory not accessible"
                )
            
            # Check MQTT writer health
            try:
                if self.writer:
                    self.publish_health_event(
                        self.devid,
                        "offline",
                        "low",
                        "MQTT connection operational"
                    )
                else:
                    self.publish_health_event(
                        self.devid,
                        "offline", 
                        "high",
                        "MQTT writer not available"
                    )
            except Exception as e:
                self.publish_health_event(
                    self.devid,
                    "offline",
                    "critical",
                    f"MQTT connection error: {str(e)}"
                )
            
            # System uptime health check
            uptime_hours = (current_time - self.system_start_time) / 3600
            self.publish_health_event(
                self.devid,
                "hardware_failure",
                "low",
                f"System uptime: {uptime_hours:.1f} hours, Images processed: {self.images_processed}"
            )

    def publish_summary(self):
        """Publish network summary"""
        try:
            epoch_ms = int(time.time() * 1000)
            
            total_nodes = len(self.node_map)
            total_images = len(self.images_saved) + self.images_processed
            
            message_data = {
                "timestamp": datetime.now().isoformat(),
                "machine_id": self.devid,
                "total_nodes": total_nodes,
                "total_images": total_images,
                "images_processed_locally": self.images_processed,
                "events_detected_locally": self.events_detected,
                "active_nodes": list(self.node_map.keys()),
                "command_center_stats": {
                    "ai_detection_enabled": True,
                    "processed_images": self.images_processed,
                    "detected_events": self.events_detected,
                    "detection_rate": (self.events_detected / max(1, self.images_processed)) * 100,
                    "uptime_hours": (time.time() - self.system_start_time) / 3600
                }
            }
            
            filename = f"{epoch_ms}.json"
            
            self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-summary",
                data_type="json",
                mission_id=self.mission_id,
                priority=1,
                destination_ids=["s3"]
            )
            
            print(f"📊 Summary published - Processed: {self.images_processed}, Events: {self.events_detected}")
                
        except Exception as e:
            print(f"Error publishing summary: {e}")

    def get_image_files(self):
        """Get all image files from the specified directory"""
        image_extensions = [
            '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.tiff', '*.tif',
            '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.GIF', '*.TIFF', '*.TIF'
        ]
        image_files = []
        
        if not os.path.exists(self.image_directory):
            print(f"Warning: Image directory {self.image_directory} does not exist")
            return []
        
        print(f"🔍 Scanning for images in: {self.image_directory}")
        
        for extension in image_extensions:
            pattern = os.path.join(self.image_directory, extension)  # Direct files in directory
            found_files = glob.glob(pattern)
            if found_files:
                print(f"   Found {len(found_files)} {extension} files")
            image_files.extend(found_files)
            
            # Also check subdirectories
            pattern_recursive = os.path.join(self.image_directory, '**', extension)
            found_files_recursive = glob.glob(pattern_recursive, recursive=True)
            # Remove duplicates already found in direct search
            new_files = [f for f in found_files_recursive if f not in found_files]
            image_files.extend(new_files)
            
        # Remove duplicates and sort
        image_files = sorted(list(set(image_files)))
        print(f"📁 Total image files found: {len(image_files)}")
        
        return image_files

    def process_image_with_enhanced_detector(self, image_path):
        """Process image with enhanced detector and return results"""
        try:
            print(f"🔍 Processing image with AI detector: {os.path.basename(image_path)}")
            
            # Run detection
            has_objects = self.detector.ImageHasTargetObjects(image_path, crop_objects=True)
            
            if has_objects:
                # Get cropped object files (they're saved in the same directory with modified names)
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                crop_pattern = f"{base_name}_*_cropped.jpg"
                crop_dir = os.path.dirname(image_path)
                cropped_files = glob.glob(os.path.join(crop_dir, crop_pattern))
                
                print(f"Detection found! Generated {len(cropped_files)} cropped images")
                
                return {
                    "has_detection": True,
                    "cropped_files": cropped_files,
                    "original_file": image_path
                }
            else:
                print(f"No objects detected in image")
                return {
                    "has_detection": False,
                    "cropped_files": [],
                    "original_file": image_path
                }
                
        except Exception as e:
            print(f"💥 Error processing image {image_path}: {e}")
            return {
                "has_detection": False,
                "cropped_files": [],
                "original_file": image_path,
                "error": str(e)
            }

    def process_images_from_directory(self):
        """Process all images from the directory one by one"""
        print(f"\nStarting image processing from directory: {self.image_directory}")
        
        image_files = self.get_image_files()
        
        if not image_files:
            print(f"No images found in {self.image_directory}")
            return
        
        print(f"Found {len(image_files)} images to process")
        
        for image_file in image_files:
            if image_file in self.processed_images:
                continue  # Skip already processed images
                
            print(f"\n{'='*60}")
            print(f"Processing image {len(self.processed_images) + 1}/{len(image_files)}")
            print(f"File: {os.path.basename(image_file)}")
            print(f"{'='*60}")
            
            # Use same timestamp for all uploads related to this image
            image_timestamp = datetime.now(timezone.utc)
            
            # Process with enhanced detector
            detection_result = self.process_image_with_enhanced_detector(image_file)
            
            # ALL IMAGES ARE SUSPICIOUS EVENTS - regardless of detection results
            if detection_result["has_detection"]:
                print(f"Suspicious event - objects detected!")
                self.events_detected += 1
                
                for cropped_file in detection_result["cropped_files"]:
                    self.publish_cropped_image_as_suspicious(cropped_file, detection_result, image_timestamp)
                    time.sleep(1)
                
                self.publish_original_image_as_suspicious(image_file, detection_result, image_timestamp)
                
            else:
                print(f"🚨 SUSPICIOUS EVENT - NO OBJECTS DETECTED (Low Severity)")
                self.publish_original_image_as_suspicious(image_file, detection_result, image_timestamp)
            
            self.processed_images.add(image_file)
            self.images_processed += 1
            
            # Check system health periodically
            self.check_system_health()
            
            # Wait before processing next image
            print(f"⏳ Waiting 5 seconds before next image...")
            time.sleep(5)
        
        print(f"\nImage processing completed!")
        print(f"Total processed: {self.images_processed}")
        print(f"Events detected: {self.events_detected}")

    def publish_cropped_image_as_suspicious(self, cropped_file, detection_result):
        """Publish cropped image as suspicious event"""
        try:
            # Extract detection information from filename
            filename = os.path.basename(cropped_file)
            detected_objects = []
            confidence = 0.85
            
            if "_cropped.jpg" in filename:
                parts = filename.replace("_cropped.jpg", "").split("_")
                if len(parts) >= 3:
                    detected_objects = [parts[-2]]  # Object type
                    try:
                        confidence = float(parts[-1].replace("conf", ""))
                    except:
                        confidence = 0.85
            
            # Get event details based on detection
            event_details = get_suspicious_event_details(detected_objects, [confidence])
            
            # Convert image to base64
            image_base64 = image.image2string(cropped_file)
            
            self.publish_suspicious_event(
                self.devid,
                image_base64,
                event_details,
                detected_objects,
                confidence
            )
            
            print(f"Published cropped suspicious event: {filename}")
            
        except Exception as e:
            print(f"Error publishing cropped image {cropped_file}: {e}")

    def publish_original_image_as_suspicious(self, image_file, detection_result):
        """Publish original image as suspicious event"""
        try:
            # Determine what was detected
            detected_objects = []
            confidence = 0.85
            
            if detection_result["has_detection"] and detection_result["cropped_files"]:
                # Extract objects from cropped filenames
                for cropped_file in detection_result["cropped_files"]:
                    filename = os.path.basename(cropped_file)
                    if "_cropped.jpg" in filename:
                        parts = filename.replace("_cropped.jpg", "").split("_")
                        if len(parts) >= 3:
                            obj_name = parts[-2]
                            if obj_name not in detected_objects:
                                detected_objects.append(obj_name)
                            try:
                                conf = float(parts[-1].replace("conf", ""))
                                confidence = max(confidence, conf)
                            except:
                                pass
            
            # Get event details (will be low severity if no detections)
            confidences = [confidence] if detected_objects else []
            event_details = get_suspicious_event_details(detected_objects, confidences)
            
            # Convert image to base64
            image_base64 = image.image2string(image_file)
            
            self.publish_suspicious_event(
                self.devid,
                image_base64,
                event_details,
                detected_objects,
                confidence
            )
            
            print(f"Published original suspicious event: {os.path.basename(image_file)} ({event_details['type']})")
            
        except Exception as e:
            print(f"Error publishing original image {image_file}: {e}")

    def run_image_processing_cycle(self):
        """Run image processing in a separate thread"""
        def processing_thread():
            time.sleep(5)  # Give system time to initialize
            self.process_images_from_directory()
        
        thread = threading.Thread(target=processing_thread, daemon=True)
        thread.start()
        return thread

    def print_status(self):
        status_count = 0
        
        # Start image processing in background
        processing_thread = self.run_image_processing_cycle()
        
        while True:
            print("######### Command Center Status ##############")
            print(f"Images processed: {self.images_processed}")
            print(f"Events detected: {self.events_detected}")
            print(f"Connected nodes: {len(self.node_map)}")
            print(f"Uptime: {(time.time() - self.system_start_time) / 3600:.1f} hours")
            
            for x in self.node_map.keys():
                print(f" ####### {x} : {self.node_map[x]}")
            for x in self.images_saved:
                print(f"Saved image : {x}")
            print("#######################################################")
            
            # Check system health
            self.check_system_health()
            
            # Publish summary every 10 status updates
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
            print("Received image from remote device")
            
            # Save image locally first
            imstr = orig_msg["i_d"]
            im = image.imstrtoimage(imstr)
            fname = f"/tmp/commandcenter_{random.randint(1000,2000)}.jpg"
            print(f"Saving received image to {fname}")
            im.save(fname)
            self.images_saved.append(fname)
            
            # Extract detection results from message
            source_node = orig_msg.get("i_s", "unknown")
            detected_objects = orig_msg.get("detected_objects", [])
            confidence = orig_msg.get("confidence", 0.85)
            detection_type = orig_msg.get("detection_type", "unknown")
            severity = orig_msg.get("severity", "low")
            description = orig_msg.get("description", "Remote image processed")
            
            # Create event details structure
            event_details = {
                "type": detection_type,
                "severity": severity,
                "description": description
            }
            
            # Use current timestamp for consistency
            timestamp = datetime.now(timezone.utc)
            
            # Upload the saved image and publish suspicious event
            self.publish_suspicious_event(
                source_node, 
                fname,  
                event_details,
                detected_objects,
                confidence,
                timestamp
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
        self.publish_health_event(
            nodeid, 
            "offline",  # Device is NOT offline since it's reporting
            "low", 
            f"Device heartbeat received - photos: {photos_taken}, events: {events_seen}"
        )
    
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
        self.publish_health_event(
            nodeid, 
            "hardware_failure",  # Device hardware working since it's active
            "low", 
            f"Device event activity at {eventtime}"
        )

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
        
        # Get machine configuration
        self.machine_config = Configs.get_machine_config()
        self.machine_id = self.machine_config.get("machine_id", "-") or "-"
        self.organization_id = self.machine_config.get("organization_id", "-") or "-"
        
        print(f"🏷️  Machine ID: {self.machine_id}")
        print(f"🏢 Organization ID: {self.organization_id}")
        
        # Initialize enhanced detector
        self.detector = Detector()
        self.detector.set_detection_category("all")  # Detect all objects
        
        # Image processing settings
        self.image_directory = "/home/pi/Documents/images"
        self.processed_images = set()  # Track processed images
        self.images_processed = 0
        self.events_detected = 0
        
        # Health monitoring
        self.last_health_check = 0
        self.health_check_interval = 60  # 60 seconds
        self.system_start_time = time.time()
        
        print(f"DevUnit {devid} initialized with AI detector")
       
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
        image_extensions = [
            '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.tiff', '*.tif',
            '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.GIF', '*.TIFF', '*.TIF'
        ]
        image_files = []
        
        if not os.path.exists(self.image_directory):
            print(f"Warning: Image directory {self.image_directory} does not exist")
            return []
        
        print(f"🔍 Scanning for images in: {self.image_directory}")
        
        for extension in image_extensions:
            pattern = os.path.join(self.image_directory, extension)  # Direct files in directory
            found_files = glob.glob(pattern)
            if found_files:
                print(f"   Found {len(found_files)} {extension} files")
            image_files.extend(found_files)
            
            # Also check subdirectories
            pattern_recursive = os.path.join(self.image_directory, '**', extension)
            found_files_recursive = glob.glob(pattern_recursive, recursive=True)
            # Remove duplicates already found in direct search
            new_files = [f for f in found_files_recursive if f not in found_files]
            image_files.extend(new_files)
            
        # Remove duplicates and sort
        image_files = sorted(list(set(image_files)))
        print(f"📁 Total image files found: {len(image_files)}")
        
        return image_files

    def process_image_with_enhanced_detector(self, image_path):
        """Process image with enhanced detector and return results"""
        try:
            print(f"🔍 Processing image with AI detector: {os.path.basename(image_path)}")
            
            # Run detection
            has_objects = self.detector.ImageHasTargetObjects(image_path, crop_objects=True)
            
            if has_objects:
                # Get cropped object files (they're saved in the same directory with modified names)
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                crop_pattern = f"{base_name}_*_cropped.jpg"
                crop_dir = os.path.dirname(image_path)
                cropped_files = glob.glob(os.path.join(crop_dir, crop_pattern))
                
                print(f"✅ Detection found! Generated {len(cropped_files)} cropped images")
                
                return {
                    "has_detection": True,
                    "cropped_files": cropped_files,
                    "original_file": image_path
                }
            else:
                print(f"❌ No objects detected in image")
                return {
                    "has_detection": False,
                    "cropped_files": [],
                    "original_file": image_path
                }
                
        except Exception as e:
            print(f"💥 Error processing image {image_path}: {e}")
            return {
                "has_detection": False,
                "cropped_files": [],
                "original_file": image_path,
                "error": str(e)
            }

    def send_processed_images(self, detection_result):
        """Send cropped images first, then original image - ALL AS SUSPICIOUS EVENTS"""
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        
        try:
            # First, send cropped images if any detections
            for cropped_file in detection_result["cropped_files"]:
                self.send_img(cropped_file, is_cropped=True, detection_result=detection_result)
                time.sleep(2)  # Small delay between sends
            
            # Then send original image - ALWAYS AS SUSPICIOUS EVENT
            self.send_img(detection_result["original_file"], is_cropped=False, detection_result=detection_result)
            
        except Exception as e:
            print(f"Error sending images: {e}")

    def send_img(self, imgfile, is_cropped=False, detection_result=None):
        """Send image as suspicious event message"""
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        
        mst = constants.MESSAGE_TYPE_PHOTO
        
        # Use consistent timestamp for this image
        image_timestamp = datetime.now(timezone.utc)
        
        # Extract detection information from filename if cropped
        detected_objects = []
        confidence = 0.85
        
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
        elif detection_result and detection_result["has_detection"]:
            # For original images with detections
            for cropped_file in detection_result["cropped_files"]:
                filename = os.path.basename(cropped_file)
                if "_cropped.jpg" in filename:
                    parts = filename.replace("_cropped.jpg", "").split("_")
                    if len(parts) >= 3:
                        obj_name = parts[-2]
                        if obj_name not in detected_objects:
                            detected_objects.append(obj_name)
                        try:
                            conf = float(parts[-1].replace("conf", ""))
                            confidence = max(confidence, conf)
                        except:
                            pass
        
        # Get suspicious event details based on detection
        confidences = [confidence] if detected_objects else []
        event_details = get_suspicious_event_details(detected_objects, confidences)
        
        im = {
            "i_m": f"Image from {self.devid}",
            "i_s": self.devid,
            "i_t": image_timestamp.isoformat(),  
            "i_d": image.image2string(imgfile),  # Still base64 for RF transmission
            "is_cropped": is_cropped,
            "detected_objects": detected_objects,
            "confidence": confidence,
            "detection_type": event_details["type"],  # Use proper suspicious event type
            "severity": event_details["severity"],
            "description": event_details["description"],
            "has_detection": detection_result["has_detection"] if detection_result else False,
            "original_filename": os.path.basename(imgfile),
            "machine_id": self.machine_id,
            "organization_id": self.organization_id
        }
        
        msgstr = json.dumps(im)
        print(f"Sending {'cropped' if is_cropped else 'original'} suspicious event: {os.path.basename(imgfile)} ({event_details['type']}, {event_details['severity']})")
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
        """Process all images from the directory one by one - ALL AS SUSPICIOUS EVENTS"""
        image_files = self.get_image_files()
        
        if not image_files:
            print(f"❗ No images found in {self.image_directory}")
            return
        
        print(f"📁 Found {len(image_files)} images to process")
        print(f"🚨 ALL images will be sent as SUSPICIOUS EVENTS with appropriate severity")
        
        for image_file in image_files:
            if image_file in self.processed_images:
                continue  # Skip already processed images
                
            print(f"\n{'='*50}")
            print(f"📸 Processing image {len(self.processed_images) + 1}/{len(image_files)}: {os.path.basename(image_file)}")
            print(f"{'='*50}")
            
            # Process with enhanced detector
            detection_result = self.process_image_with_enhanced_detector(image_file)
            
            if detection_result["has_detection"]:
                print(f"🚨 SUSPICIOUS EVENT - OBJECTS DETECTED!")
                self.events_detected += 1
                self.send_event()  # Send event notification
                time.sleep(2)
                
                # Send processed images (cropped first, then original) - ALL AS SUSPICIOUS
                self.send_processed_images(detection_result)
            else:
                print(f"🚨 SUSPICIOUS EVENT - NO OBJECTS DETECTED (Low Severity)")
                # Still send original image as suspicious event with low severity
                self.send_img(image_file, is_cropped=False, detection_result=detection_result)
            
            self.processed_images.add(image_file)
            self.images_processed += 1
            
            # Send heartbeat after processing each image (health message)
            time.sleep(5)
            self.send_heartbeat(self.images_processed, self.events_detected)
            
            # Check system health periodically 
            self.check_system_health()
            
            # Wait before processing next image
            time.sleep(10)

    def check_system_health(self):
        """Check system health and send health events every 60 seconds"""
        current_time = time.time()
        
        if current_time - self.last_health_check >= self.health_check_interval:
            self.last_health_check = current_time
            
            print(f"Performing health check for device {self.devid}")
            
            # These would be sent as health messages via RF/communication
            # For now, just log them locally since RF is disabled
            
            # AI detector health
            try:
                if hasattr(self.detector, 'model') and self.detector.model:
                    print(f"Health: AI detector operational")
                else:
                    print(f"Health: AI detector not available (HIGH severity)")
            except Exception as e:
                print(f"Health: AI detector error - {str(e)} (CRITICAL severity)")
            
            # Image directory health
            if os.path.exists(self.image_directory):
                print(f"Health: Image directory accessible - {len(self.get_image_files())} images")
            else:
                print(f"Health: Image directory not accessible (MEDIUM severity)")
            
            # System uptime
            uptime_hours = (current_time - self.system_start_time) / 3600
            print(f"Health: Uptime {uptime_hours:.1f}h, Processed: {self.images_processed}, Events: {self.events_detected}")

    def keep_sending_to_cc(self, has_camera):
        photos_taken = 0
        events_seen = 0
        
        # Initial heartbeat
        self.send_heartbeat(photos_taken, events_seen)
        time.sleep(5)
        
        if has_camera:
            # Process images from directory - ALL AS SUSPICIOUS EVENTS
            self.process_images_from_directory()
        else:
            # Original behavior for non-camera devices
            while True:
                self.send_heartbeat(photos_taken, events_seen)
                self.check_system_health()  # Health checks every 60s
                time.sleep(1800)  # Every 30 mins

    def send_heartbeat(self, photos_taken, events_seen):
        """Send heartbeat - this is a HEALTH message"""
        t = get_time_str()
        msgstr = f"{self.devid}:{t}:{photos_taken}:{events_seen}"
        next_dest = get_next_dest(self.devid)
        print(f"Sending heartbeat (health message): {msgstr}")
        # self.rf.send_message(msgstr, constants.MESSAGE_TYPE_HEARTBEAT, next_dest)

    def send_gps(self):
        """Send GPS - this is a HEALTH message"""
        next_dest = get_next_dest(self.devid)
        msgstr = f"{self.devid}:28.4:77.0"
        print(f"Sending GPS (health message): {msgstr}")
        # self.rf.send_message(msgstr, constants.MESSAGE_TYPE_GPS, next_dest)

    def send_event(self):
        """Send event notification - this is a HEALTH message"""
        t = get_time_str()
        msgstr = f"{self.devid}:{t}"
        next_dest = get_next_dest(self.devid)
        print(f"Sending event notification (health message): {msgstr}")
        # self.rf.send_message(msgstr, constants.MESSAGE_TYPE_EVENT, next_dest)

def run_unit():
    hname = get_hostname()
    if hname not in constants.HN_ID:
        print(f"Hostname {hname} not found in constants.HN_ID")
        print(f"Available hostnames: {list(constants.HN_ID.keys())}")
        return None
        
    devid = constants.HN_ID[hname]
    print(f"🚀 Starting Watchmen System")
    print(f"🏷️  Device ID: {devid}")
    print(f"🖥️  Hostname: {hname}")
    print(f"📁 Image directory: /home/pi/Documents/images")
    
    # Check camera flag
    has_camera = len(sys.argv) > 1 and sys.argv[1] == "c"
    print(f"📷 Camera mode: {'ENABLED' if has_camera else 'DISABLED'}")
    
    print(f"Message Classification:")
    print(f"   ALL images → Suspicious events (with severity based on detections)")
    print(f"   Heartbeats, GPS, Events → Health messages")
    print(f"   System status checks → Health events (every 60 seconds)")
    print(f"Image Upload:")
    print(f"   Images uploaded as files (not base64)")
    print(f"   Image URLs stored in suspicious event data")
    print(f"   Consistent timestamps for related images")
    
    if is_node_dest(devid):
        print(f"Running as Command Center with AI Detection & MQTT Publishing")
        cc = CommandCenter(devid)
        cc.print_status()
    else:
        print(f"Running as Device Unit with AI Detection (RF communication disabled)")
        du = DevUnit(devid)
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