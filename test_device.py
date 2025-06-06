import json
import time
import constants
from datetime import datetime
from typing import Optional, Dict, Any

from test_camera import USBCamera 

class Device:
    def __init__(self, devid: str, fcomm=None, ncomm=None, mission_id: str = "watchmen_surveillance"):
        self.devid = devid
        self.mission_id = mission_id
        self.neighbours_seen = []
        self.spath = []
        
        # COMMUNICATION DISABLED - ESP and other device communication not working
        self.fcomm = None  # Disabled
        self.ncomm = None  # Disabled
        
        # if fcomm is None and ncomm is None:
        #     print("At least one communicator required")
        #     return None
        # if fcomm is not None and ncomm is not None:
        #     print("At most one communicator allowed")
        #     return None
            
        print(f"Device {devid} initialized in standalone mode (communication disabled)")
        
        # Initialize USB camera system for specific devices
        self.camera = None
        self.detector = None
        
        # Camera-enabled devices (can be configured based on device ID pattern)
        if self._is_camera_device(devid):
            self._initialize_camera_system()
        
        # Statistics
        self.image_count = 0
        self.event_count = 0
        self.health_events = []
        self.suspicious_events = []
        self.last_activity_timestamp = time.time()
        
    def _is_camera_device(self, devid: str) -> bool:
        """Determine if this device should have camera capabilities"""
        # Configure which devices have cameras - can be based on device ID pattern
        camera_device_patterns = ["AAAaaa", "CAM", "WATCH"]
        return any(pattern in devid for pattern in camera_device_patterns)
        
    def _initialize_camera_system(self):
        """Initialize the USB camera system"""
        if USBCamera is None:
            print(f"Warning: USB camera not available for device {self.devid}")
            return
            
        try:
            self.camera = USBCamera(self.devid, self.mission_id)
            self.camera.start()
            print(f"USB camera system initialized for device {self.devid}")
        except Exception as e:
            print(f"Failed to initialize USB camera for device {self.devid}: {e}")
            self.camera = None

    def send_message(self, msg: Dict[str, Any], dest: Optional[str] = None) -> bool:
        """Send message via available communicator - DISABLED: Communication not working"""
        # COMMUNICATION DISABLED - ESP and other device communication not working
        # try:
        #     if self.fcomm is not None:
        #         return self.fcomm.send_to_network(msg, self.devid, dest)
        #     if self.ncomm is not None:
        #         msgstr = json.dumps(msg)
        #         return self.ncomm.send_message(msgstr, dest)
        # except Exception as e:
        #     print(f"Failed to send message from {self.devid}: {e}")
        #     return False
        
        # Just log the message locally since communication is disabled
        print(f"[COMM DISABLED] {self.devid} would send to {dest}: {msg.get('mst', 'unknown_type')}")
        return False  # Always return False since communication is disabled

    def get_next_on_spath(self) -> Optional[str]:
        """Get next device on shortest path"""
        if len(self.spath) <= 1 or self.spath[0] != self.devid:
            print(f"{self.devid}: No next path available yet")
            return None
        return self.spath[1]

    def send_scan(self, ts: int) -> bool:
        """Send network discovery scan message"""
        scan_msg = {
            constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_SCAN,
            constants.JK_SOURCE: self.devid,
            constants.JK_LAST_SENDER: self.devid,
            constants.JK_SOURCE_TIMESTAMP: ts,
        }
        return self.send_message(scan_msg)

    def make_hb_msg(self, ts: int) -> Optional[Dict[str, Any]]:
        """Create heartbeat message"""
        if self.spath is None or len(self.spath) < 2 or self.spath[0] != self.devid:
            print(f"{self.devid}: Shortest path not adequate {self.spath}")
            return None
            
        hb_msg = {
            constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_HEARTBEAT,
            constants.JK_SOURCE: self.devid,
            constants.JK_SOURCE_TIMESTAMP: ts,
            # Payload
            constants.JK_NEIGHBOURS: self.neighbours_seen,
            constants.JK_IMAGE_COUNT: self.image_count,
            constants.JK_EVENT_COUNT: self.event_count,
            constants.JK_SHORTEST_PATH: self.spath,
            # Routing info
            constants.JK_DEST: None,  # Will get rerouted
            constants.JK_PATH_SO_FAR: [],
            constants.JK_LAST_TS: ts,
            # Additional device status
            "device_status": self._get_device_status(),
            "last_activity": self.last_activity_timestamp
        }
        return hb_msg

    def _get_device_status(self) -> Dict[str, Any]:
        """Get current device status for heartbeat"""
        status = {
            "camera_enabled": self.camera is not None,
            "health_events_count": len(self.health_events),
            "suspicious_events_count": len(self.suspicious_events),
            "uptime": time.time() - self.last_activity_timestamp if hasattr(self, 'start_time') else 0
        }
        
        if self.camera:
            status.update({
                "images_processed": self.camera.image_count,
                "detections_made": self.camera.detection_count,
                "last_capture_time": getattr(self.camera, 'last_capture_time', 0)
            })
            
        return status

    def make_image_msg(self, ts: int, image_data: str, image_ts: int) -> Optional[Dict[str, Any]]:
        """Create image transmission message"""
        if self.spath is None or len(self.spath) < 2 or self.spath[0] != self.devid:
            print(f"{self.devid}: Cannot send image, no valid path")
            return None
            
        image_msg = {
            constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_PHOTO,
            constants.JK_SOURCE: self.devid,
            constants.JK_SOURCE_TIMESTAMP: ts,
            # Payload
            constants.JK_IMAGE_DATA: image_data,
            constants.JK_IMAGE_TS: image_ts,
            # Routing info
            constants.JK_DEST: None,  # Will get rerouted
            constants.JK_PATH_SO_FAR: [],
            constants.JK_LAST_TS: ts,
            # Additional metadata
            "image_source": "usb_camera",
            "processing_info": "ai_processed"
        }
        return image_msg

    def spread_spath(self, msg: Dict[str, Any]):
        """Spread shortest path information to neighbors"""
        source = msg[constants.JK_SOURCE]
        dest = msg[constants.JK_DEST]
        source_ts = msg[constants.JK_SOURCE_TIMESTAMP]
        spath1 = msg[constants.JK_SHORTEST_PATH]
        
        if len(self.spath) == 0 or len(spath1) < len(self.spath):
            print(f"********* {self.devid}: Updating spath from {self.spath} to {spath1[::-1]}")
            self.spath = spath1[::-1]

            for neighbour in self.neighbours_seen:
                if neighbour in spath1:
                    continue
                new_msg = msg.copy()
                new_msg[constants.JK_DEST] = neighbour
                new_msg[constants.JK_SHORTEST_PATH] = spath1 + [neighbour]
                self.send_message(new_msg, neighbour)

    def get_next_dest(self, msg: Dict[str, Any]) -> Optional[str]:
        """Get next destination for message routing"""
        path_so_far = msg[constants.JK_PATH_SO_FAR]
        new_dest = self.get_next_on_spath()
        if new_dest in path_so_far:
            print(f"{self.devid}: new_dest: {new_dest} is in {path_so_far}")
            return None
        return new_dest
    
    def propogate_msg_to_next(self, msg: Dict[str, Any], new_dest: str) -> bool:
        """Propagate message to next destination"""
        new_msg = msg.copy()
        new_msg[constants.JK_DEST] = new_dest
        new_msg[constants.JK_PATH_SO_FAR] = msg[constants.JK_PATH_SO_FAR] + [self.devid]
        new_msg[constants.JK_LAST_TS] = time.time_ns()
        return self.send_message(new_msg, new_dest)

    def propogate_message(self, msg: Dict[str, Any]) -> bool:
        """Propagate message through network with fallback routing"""
        new_dest = self.get_next_dest(msg)
        sent = False
        
        if new_dest is not None:
            sent = self.propogate_msg_to_next(msg, new_dest)
            
        path_so_far = msg[constants.JK_PATH_SO_FAR]
        if not sent:
            print(f"{self.devid}: Failed to send to {new_dest}: Trying alternative route")
            for n in self.neighbours_seen:
                if n in path_so_far or n == new_dest:
                    continue
                new_dest = n
                sent = self.propogate_msg_to_next(msg, new_dest)
                if sent:
                    print(f"{self.devid}: Successfully delivered to {new_dest}")
                    break
                    
        return sent

    def send_hb(self, ts: int) -> bool:
        """Send heartbeat message"""
        msg = self.make_hb_msg(ts)
        if msg is not None:
            return self.propogate_message(msg)
        return False

    def send_image(self, ts: int, imdatastr: str, image_ts: int) -> bool:
        """Send image data through network"""
        msg = self.make_image_msg(ts, imdatastr, image_ts)
        if msg is not None:
            return self.propogate_message(msg)
        return False

    def process_msg(self, msg: Dict[str, Any]):
        """Process incoming messages"""
        mtype = msg[constants.JK_MESSAGE_TYPE]
        
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg[constants.JK_SOURCE]
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
                print(f"{self.devid}: Discovered new neighbor: {source}")
                
        elif mtype == constants.MESSAGE_TYPE_SPATH:
            self.spread_spath(msg)
            
        # Passthrough routing for other message types
        elif mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.propogate_message(msg)
            
        elif mtype == constants.MESSAGE_TYPE_PHOTO:
            self.propogate_message(msg)

    def check_event(self):
        """Check for events using USB camera system"""
        if self.camera is None:
            return
            
        try:
            print(f"###### {self.devid}: Checking for events via USB camera ######")
            
            # Trigger USB image capture and processing
            image_ts = time.time_ns()
            (imfile, result) = self.camera.take_picture()
            
            if imfile:
                self.image_count += 1
                print(f"###### {self.devid}: USB image processing completed: {result} ######")
                
                # Check if any suspicious events were detected
                if self.camera.suspicious_events:
                    # Get the latest suspicious event
                    latest_event = self.camera.suspicious_events[-1]
                    
                    # Send image data if event detected
                    if latest_event['confidence'] > 0.7:  # Confidence threshold
                        print(f"###### {self.devid}: High confidence detection, sending image ######")
                        # For now, send a summary instead of full image data
                        summary_data = json.dumps({
                            "event_type": latest_event['type'],
                            "confidence": latest_event['confidence'],
                            "timestamp": latest_event['timestamp'],
                            "image_path": imfile
                        })
                        
                        self.send_image(time.time_ns(), summary_data, image_ts)
                        self.event_count += 1
                        
                # Update activity timestamp
                self.last_activity_timestamp = time.time()
                
            else:
                print(f"###### {self.devid}: No images captured: {result} ######")
                
        except Exception as e:
            print(f"###### {self.devid}: Event check failed: {e} ######")
            if self.camera:
                self.camera._record_health_event('hardware_failure', 'medium', f"Event check failed: {e}")

    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive device status summary"""
        summary = {
            "device_id": self.devid,
            "mission_id": self.mission_id,
            "timestamp": datetime.now().isoformat(),
            "network_status": {
                "neighbors_count": len(self.neighbours_seen),
                "neighbors": self.neighbours_seen,
                "shortest_path": self.spath,
                "has_path_to_cc": len(self.spath) > 1
            },
            "activity_stats": {
                "images_processed": self.image_count,
                "events_detected": self.event_count,
                "last_activity": self.last_activity_timestamp
            },
            "camera_status": {
                "enabled": self.camera is not None,
            }
        }
        
        if self.camera:
            summary["camera_status"].update({
                "total_images": self.camera.image_count,
                "total_detections": self.camera.detection_count,
                "health_events": len(self.camera.health_events),
                "suspicious_events": len(self.camera.suspicious_events)
            })
            
        return summary

    def cleanup(self):
        """Cleanup device resources"""
        try:
            if self.camera:
                self.camera.cleanup()
            print(f"Device {self.devid} cleaned up successfully")
        except Exception as e:
            print(f"Device {self.devid} cleanup failed: {e}")

def main():
    """Test the device with USB camera - Communication disabled"""
    print("Testing Device with USB Camera System (Standalone Mode)")
    
    # Create a test device with camera capabilities - no communication
    device = Device("CAM_TEST_001", mission_id="test_mission")
    
    try:
        # Test scan functionality (will be logged only, not sent)
        device.send_scan(time.time_ns())
        
        # Test event checking (camera capture) - this is the main functionality
        device.check_event()
        
        # Test heartbeat (will be logged only, not sent)
        device.send_hb(time.time_ns())
        
        # Print status summary
        status = device.get_status_summary()
        print("Device Status Summary:")
        print(json.dumps(status, indent=2))
        
        # Print camera events if available
        if device.camera:
            events = device.camera.get_events_for_central()
            print("\nCamera Events for Central Device:")
            print(json.dumps(events, indent=2))
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        device.cleanup()

if __name__ == "__main__":
    main()