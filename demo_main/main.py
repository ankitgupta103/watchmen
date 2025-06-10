from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import threading
import json
import socket
import random
import glob
from pathlib import Path

import constants
from detect_enhanced import Detector
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson
from vyomcloudbridge.utils.configs import Configs
from vyomcloudbridge.utils.common import get_mission_upload_dir
from rf_comm import RFComm
import image

def get_hostname():
    return socket.gethostname()

def get_device_id():
    hname = get_hostname()
    return constants.HN_ID.get(hname)

def is_node_src(devid):
    return constants.PATH_DEMOB[0] == devid

def is_node_dest(devid):
    return constants.PATH_DEMOB[-1] == devid

def is_node_passthrough(devid):
    if is_node_src(devid) or is_node_dest(devid):
        return False
    return True

def get_next_dest(devid):
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
        return None  # No suspicious event if nothing detected
    
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
    """Central Device - AI Detection and MQTT Publishing for Suspicious Events Only"""
    
    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        
        # Node tracking for RF communication
        self.node_map = {}
        self.images_received_via_rf = []
        self.msgids_seen = []
        
        # MQTT Setup
        self.writer = QueueWriterJson()
        self.mission_id = "_all_"
        
        # Machine configuration
        self.machine_config = Configs.get_machine_config()
        self.machine_id = self.machine_config.get("machine_id", "-") or "-"
        self.organization_id = self.machine_config.get("organization_id", "-") or "-"
        
        # AI Detection Setup
        self.detector = Detector()
        self.detector.set_detection_category("all")
        
        # Image processing settings
        self.image_directory = "/home/pi/Documents/images"
        self.processed_images = set()
        self.images_processed = 0
        self.suspicious_events_detected = 0
        
        # Statistics
        self.system_start_time = time.time()
        
        # Ensure image directory exists
        Path(self.image_directory).mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 Command Center {devid} initialized")
        print(f"🏷️  Machine ID: {self.machine_id}")
        print(f"📁 Image directory: {self.image_directory}")
        print(f"🤖 AI Detection: ENABLED (only publishes when suspicious events detected)")
        print(f"📡 RF Communication: ENABLED")
        print(f"☁️  MQTT Publishing: ENABLED (suspicious events only)")

    def upload_image_and_get_url(self, image_path, data_source="watchmen-suspicious", timestamp=None):
        """Upload image file and return the URL"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            mission_upload_dir = get_mission_upload_dir(
                organization_id=self.organization_id,
                machine_id=self.machine_id,
                mission_id="_all_",
                data_source=data_source,
                date=timestamp.strftime("%Y-%m-%d"),
                project_id="_all_"
            )
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            original_filename = os.path.basename(image_path)
            name, ext = os.path.splitext(original_filename)
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]
            unique_filename = f"{name}_{timestamp_str}{ext}"
            
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
                image_url = f"{mission_upload_dir}/{unique_filename}"
                print(f"📤 Image uploaded: {unique_filename}")
                return image_url
            else:
                print(f"❌ Failed to upload image: {error}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading image {image_path}: {e}")
            return None

    def publish_suspicious_event(self, machine_id, image_path, event_details, detected_objects=None, confidence=0.85, timestamp=None):
        """Publish suspicious event with image upload"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
                
            epoch_ms = int(timestamp.timestamp() * 1000)
            
            # Upload image and get URL
            image_url = self.upload_image_and_get_url(image_path, "watchmen-suspicious", timestamp)
            
            if not image_url:
                return False
            
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
                print(f"🚨 SUSPICIOUS EVENT: {event_details['type']} ({event_details['severity']})")
                print(f"   Machine: {machine_id}")
                print(f"   Objects: {detected_objects}")
                print(f"   Confidence: {confidence:.2f}")
                print(f"   Image: {image_url}")
                return True
            else:
                print(f"❌ Failed to publish suspicious event: {error}")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing suspicious event: {e}")
            return False

    def get_image_files(self):
        """Get all image files from directory"""
        image_extensions = [
            '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.tiff', '*.tif',
            '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.GIF', '*.TIFF', '*.TIF'
        ]
        image_files = []
        
        if not os.path.exists(self.image_directory):
            return []
        
        for extension in image_extensions:
            pattern = os.path.join(self.image_directory, extension)
            found_files = glob.glob(pattern)
            image_files.extend(found_files)
            
            # Check subdirectories
            pattern_recursive = os.path.join(self.image_directory, '**', extension)
            found_files_recursive = glob.glob(pattern_recursive, recursive=True)
            new_files = [f for f in found_files_recursive if f not in found_files]
            image_files.extend(new_files)
            
        return sorted(list(set(image_files)))

    def process_image_with_ai(self, image_path):
        """Process image with AI detector and return detection results"""
        try:
            print(f"🔍 AI Processing: {os.path.basename(image_path)}")
            
            # Run detection with cropping
            has_objects = self.detector.ImageHasTargetObjects(image_path, crop_objects=True)
            
            if has_objects:
                # Get cropped object files
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                crop_pattern = f"{base_name}_*_cropped.jpg"
                crop_dir = os.path.dirname(image_path)
                cropped_files = glob.glob(os.path.join(crop_dir, crop_pattern))
                
                print(f"✅ SUSPICIOUS ACTIVITY DETECTED! {len(cropped_files)} objects found")
                
                return {
                    "has_detection": True,
                    "cropped_files": cropped_files,
                    "original_file": image_path
                }
            else:
                print(f"✅ No suspicious activity detected")
                return {
                    "has_detection": False,
                    "cropped_files": [],
                    "original_file": image_path
                }
                
        except Exception as e:
            print(f"💥 AI processing error: {e}")
            return {
                "has_detection": False,
                "cropped_files": [],
                "original_file": image_path,
                "error": str(e)
            }

    def extract_objects_from_cropped_files(self, cropped_files):
        """Extract detected objects and confidence from cropped filenames"""
        detected_objects = []
        max_confidence = 0.85
        
        for cropped_file in cropped_files:
            filename = os.path.basename(cropped_file)
            if "_cropped.jpg" in filename:
                parts = filename.replace("_cropped.jpg", "").split("_")
                if len(parts) >= 3:
                    obj_name = parts[-2]
                    if obj_name not in detected_objects:
                        detected_objects.append(obj_name)
                    try:
                        conf = float(parts[-1].replace("conf", ""))
                        max_confidence = max(max_confidence, conf)
                    except:
                        pass
                        
        return detected_objects, max_confidence

    def process_images_from_directory(self):
        """Process images from directory - only publish if suspicious events detected"""
        print(f"\n🔍 Starting AI analysis of images in: {self.image_directory}")
        
        image_files = self.get_image_files()
        
        if not image_files:
            print(f"📁 No images found in {self.image_directory}")
            return
        
        print(f"📸 Found {len(image_files)} images to analyze")
        
        for image_file in image_files:
            if image_file in self.processed_images:
                continue
                
            print(f"\n{'='*60}")
            print(f"Image {len(self.processed_images) + 1}/{len(image_files)}: {os.path.basename(image_file)}")
            print(f"{'='*60}")
            
            # Process with AI
            detection_result = self.process_image_with_ai(image_file)
            
            # Only publish if suspicious activity detected
            if detection_result["has_detection"]:
                print(f"🚨 PUBLISHING SUSPICIOUS EVENT")
                
                # Use same timestamp for related uploads
                event_timestamp = datetime.now(timezone.utc)
                
                # Extract detection information
                detected_objects, max_confidence = self.extract_objects_from_cropped_files(
                    detection_result["cropped_files"]
                )
                
                # Get event details
                event_details = get_suspicious_event_details(detected_objects, [max_confidence])
                
                if event_details:  # Only if truly suspicious
                    # Publish cropped images
                    for cropped_file in detection_result["cropped_files"]:
                        self.publish_suspicious_event(
                            self.devid,
                            cropped_file,
                            event_details,
                            detected_objects,
                            max_confidence,
                            event_timestamp
                        )
                        time.sleep(1)
                    
                    # Publish original image
                    self.publish_suspicious_event(
                        self.devid,
                        image_file,
                        event_details,
                        detected_objects,
                        max_confidence,
                        event_timestamp
                    )
                    
                    self.suspicious_events_detected += 1
                else:
                    print(f"🔍 Detection found but not classified as suspicious")
            else:
                print(f"✅ No suspicious activity - not publishing")
            
            self.processed_images.add(image_file)
            self.images_processed += 1
            
            print(f"⏳ Waiting 3 seconds before next image...")
            time.sleep(3)
        
        print(f"\n🎯 AI Analysis Complete!")
        print(f"   Images processed: {self.images_processed}")
        print(f"   Suspicious events: {self.suspicious_events_detected}")
        print(f"   Detection rate: {(self.suspicious_events_detected / max(1, self.images_processed)) * 100:.1f}%")

    def process_received_rf_image(self, msgstr):
        """Process image received via RF communication"""
        try:
            orig_msg = json.loads(msgstr)
            
            if "i_d" in orig_msg:
                print(f"📡 Received image via RF from device")
                
                # Save received image to directory for processing
                imstr = orig_msg["i_d"]
                im = image.imstrtoimage(imstr)
                
                # Save with timestamp and source info
                timestamp = int(time.time() * 1000)
                source_node = orig_msg.get("i_s", "unknown")
                fname = os.path.join(self.image_directory, f"rf_received_{source_node}_{timestamp}.jpg")
                
                im.save(fname)
                self.images_received_via_rf.append(fname)
                
                print(f"💾 Saved RF image: {os.path.basename(fname)}")
                print(f"🔍 Image will be processed in next AI analysis cycle")
                
        except Exception as e:
            print(f"❌ Error processing RF image: {e}")

    def process_hb_message(self, hbstr):
        """Process heartbeat message with health data"""
        try:
            # Parse heartbeat: "DeviceID:time:photos:events:lat:lng"
            parts = hbstr.split(':')
            if len(parts) >= 6:
                nodeid = parts[0]
                hbtime = parts[1]
                photos_taken = int(parts[2])
                events_seen = int(parts[3])
                lat = float(parts[4])
                lng = float(parts[5])
                
                # Update node tracking
                self.node_map[nodeid] = {
                    "last_heartbeat": hbtime,
                    "photos_taken": photos_taken,
                    "events_seen": events_seen,
                    "lat": lat,
                    "lng": lng,
                    "last_contact": time.time()
                }
                
                print(f"💓 Heartbeat from {nodeid}: GPS({lat}, {lng}), Photos:{photos_taken}, Events:{events_seen}")
                
                # Publish health event via MQTT
                self.publish_health_event_for_device(nodeid, lat, lng, photos_taken, events_seen)
                
        except Exception as e:
            print(f"❌ Error processing heartbeat: {e}")

    def publish_health_event_for_device(self, device_id, lat, lng, photos_taken, events_seen):
        """Publish health event for device based on heartbeat"""
        try:
            epoch_ms = int(time.time() * 1000)
            
            message_data = {
                "event_type": "health",
                "machine_id": device_id,
                "machine_name": f"{device_id}",
                "timestamp": datetime.now().isoformat(),
                "type": "offline",  # Device is NOT offline since sending heartbeat
                "severity": "low",
                "details": f"Device active - GPS: ({lat}, {lng}), Photos: {photos_taken}, Events: {events_seen}",
                "location": {
                    "lat": lat,
                    "lng": lng
                },
                "device_stats": {
                    "photos_taken": photos_taken,
                    "events_seen": events_seen
                },
                "reported_by": self.devid
            }
            
            filename = f"{epoch_ms}.json"
            
            success, error = self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-health",
                data_type="json",
                mission_id=self.mission_id,
                priority=1,
                destination_ids=["s3"]
            )
            
            if success:
                print(f"💊 Health event published for {device_id}")
            else:
                print(f"❌ Failed to publish health event: {error}")
                
        except Exception as e:
            print(f"❌ Error publishing health event: {e}")

    def process_msg(self, msgid, mst, msgstr):
        """Process incoming RF messages"""
        if msgid in self.msgids_seen:
            return
        self.msgids_seen.append(msgid)
        
        if mst == constants.MESSAGE_TYPE_PHOTO:
            print(f"📡 Received image via RF")
            self.process_received_rf_image(msgstr)
        elif mst == constants.MESSAGE_TYPE_HEARTBEAT:
            print(f"💓 Received heartbeat via RF")
            self.process_hb_message(msgstr)
        elif mst == constants.MESSAGE_TYPE_EVENT:
            print(f"📡 Received event via RF: {msgstr}")

    def run_ai_analysis_cycle(self):
        """Run AI analysis in background thread"""
        def analysis_thread():
            time.sleep(5)  # Wait for system initialization
            while True:
                try:
                    self.process_images_from_directory()
                    print(f"⏳ Waiting 60 seconds before next AI analysis cycle...")
                    time.sleep(60)  # Analyze every 60 seconds
                except Exception as e:
                    print(f"❌ AI analysis cycle error: {e}")
                    time.sleep(30)
        
        thread = threading.Thread(target=analysis_thread, daemon=True)
        thread.start()
        return thread

    def print_status(self):
        """Main status loop"""
        print(f"🚀 Command Center starting continuous operation...")
        
        # Start AI analysis in background
        self.run_ai_analysis_cycle()
        
        status_count = 0
        while True:
            try:
                print(f"\n{'='*60}")
                print(f"COMMAND CENTER STATUS - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*60}")
                print(f"🖼️  Images processed: {self.images_processed}")
                print(f"🚨 Suspicious events detected: {self.suspicious_events_detected}")
                print(f"📡 RF images received: {len(self.images_received_via_rf)}")
                print(f"💓 Connected devices: {len(self.node_map)}")
                print(f"⏰ Uptime: {(time.time() - self.system_start_time) / 3600:.1f} hours")
                
                # Show connected devices
                for node_id, node_data in self.node_map.items():
                    last_contact = time.time() - node_data["last_contact"]
                    print(f"   📱 {node_id}: GPS({node_data['lat']}, {node_data['lng']}), "
                          f"Last contact: {last_contact:.0f}s ago")
                
                print(f"{'='*60}")
                
                status_count += 1
                time.sleep(10)
                
            except KeyboardInterrupt:
                print(f"\n🛑 Shutting down Command Center...")
                break
            except Exception as e:
                print(f"❌ Status loop error: {e}")
                time.sleep(5)


class DevUnit:
    """Device Unit - RF Image Transmission + Heartbeat with GPS"""
    
    def __init__(self, devid, lat=28.4241, lng=77.0358):
        self.devid = devid
        self.lat = lat
        self.lng = lng
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        
        # Device statistics
        self.photos_taken = 0
        self.events_seen = 0
        
        # Image directory for local captures
        self.capture_directory = "/home/pi/Documents/captures"
        Path(self.capture_directory).mkdir(parents=True, exist_ok=True)
        
        print(f"📱 Device Unit {devid} initialized")
        print(f"📍 GPS Location: ({lat}, {lng})")
        print(f"📡 RF Communication: ENABLED")
        print(f"📷 Image Capture: ENABLED")

    def process_msg(self, msgid, mst, msgstr):
        """Process incoming RF messages (mostly for passthrough)"""
        next_dest = get_next_dest(self.devid)
        if next_dest and not is_node_dest(self.devid):
            # Passthrough message
            self.rf.send_message(msgstr, mst, next_dest)

    def capture_and_send_image(self, image_path):
        """Capture image and send via RF"""
        try:
            print(f"📸 Sending image via RF: {os.path.basename(image_path)}")
            
            # Create image message with metadata
            im_data = {
                "i_m": "Image from device",
                "i_s": self.devid,
                "i_t": str(int(time.time())),
                "i_d": image.image2string(image_path),
                "lat": self.lat,
                "lng": self.lng
            }
            
            msgstr = json.dumps(im_data)
            next_dest = get_next_dest(self.devid)
            
            if next_dest:
                success = self.rf.send_message(msgstr, constants.MESSAGE_TYPE_PHOTO, next_dest)
                if success:
                    print(f"📡 Image sent successfully to {next_dest}")
                    self.photos_taken += 1
                    self.events_seen += 1
                else:
                    print(f"❌ Failed to send image to {next_dest}")
            else:
                print(f"❌ No next destination found for {self.devid}")
                
        except Exception as e:
            print(f"❌ Error sending image: {e}")

    def send_heartbeat(self):
        """Send heartbeat with GPS location and statistics"""
        try:
            timestamp = get_time_str()
            # Format: "DeviceID:time:photos:events:lat:lng"
            msgstr = f"{self.devid}:{timestamp}:{self.photos_taken}:{self.events_seen}:{self.lat}:{self.lng}"
            
            next_dest = get_next_dest(self.devid)
            if next_dest:
                success = self.rf.send_message(msgstr, constants.MESSAGE_TYPE_HEARTBEAT, next_dest)
                if success:
                    print(f"💓 Heartbeat sent to {next_dest} - GPS({self.lat}, {self.lng})")
                else:
                    print(f"❌ Failed to send heartbeat to {next_dest}")
            
        except Exception as e:
            print(f"❌ Error sending heartbeat: {e}")

    def simulate_image_capture(self):
        """Simulate capturing images (replace with actual camera code)"""
        # For demo - send test images if available
        test_images = glob.glob("/home/pi/Documents/test_images/*.jpg")
        if test_images:
            selected_image = random.choice(test_images)
            self.capture_and_send_image(selected_image)
        else:
            print(f"📷 No test images found in /home/pi/Documents/test_images/")

    def run_device_operations(self):
        """Main device operation loop"""
        print(f"📱 Device {self.devid} starting operations...")
        
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                print(f"\n📱 Device Cycle #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Send heartbeat every cycle
                self.send_heartbeat()
                time.sleep(5)
                
                # Simulate image capture every few cycles
                if cycle_count % 3 == 0:  # Every 3rd cycle
                    print(f"📸 Simulating image capture...")
                    self.simulate_image_capture()
                
                # Wait before next cycle
                print(f"⏳ Waiting 30 seconds before next cycle...")
                time.sleep(30)
                
            except KeyboardInterrupt:
                print(f"\n🛑 Shutting down Device {self.devid}...")
                break
            except Exception as e:
                print(f"❌ Device operation error: {e}")
                time.sleep(10)


def main():
    """Main entry point"""
    try:
        hname = get_hostname()
        devid = get_device_id()
        
        if not devid:
            print(f"❌ Hostname {hname} not found in constants.HN_ID")
            print(f"Available hostnames: {list(constants.HN_ID.keys())}")
            return
            
        print(f"🚀 Starting Watchmen System")
        print(f"🏷️  Device ID: {devid}")
        print(f"🖥️  Hostname: {hname}")
        
        if is_node_dest(devid):
            print(f"🎯 Running as COMMAND CENTER")
            print(f"   - AI Detection enabled")
            print(f"   - MQTT publishing for suspicious events only")
            print(f"   - Health events from device heartbeats")
            cc = CommandCenter(devid)
            cc.print_status()
            
        elif is_node_src(devid):
            print(f"📱 Running as SOURCE DEVICE")
            print(f"   - RF image transmission enabled") 
            print(f"   - GPS heartbeat enabled")
            
            # Get GPS coordinates (could be from config or GPS module)
            lat = 28.4241  # Default coordinates
            lng = 77.0358
            
            device = DevUnit(devid, lat, lng)
            device.run_device_operations()
            
        else:
            print(f"🔄 Running as PASSTHROUGH DEVICE")
            print(f"   - RF message relay enabled")
            device = DevUnit(devid)
            device.run_device_operations()
            
    except KeyboardInterrupt:
        print(f"\n🛑 System shutdown complete")
    except Exception as e:
        print(f"❌ System error: {e}")

if __name__ == "__main__":
    main()