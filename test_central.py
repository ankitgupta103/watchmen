import json
import time
import io
import base64
from PIL import Image
from datetime import datetime
from typing import Dict, List, Any, Optional

import image
import constants

from vyomcloudbridge.services.queue_writer_json import QueueWriterJson

class NodeInfo:
    def __init__(self, devid):
        self.devid = devid
        self.hb_count = 0
        self.latest_hb_ts = 0
        self.all_hb_ts = []
        self.neighbours = []
        self.shortest_path = []
        self.paths_seen = []
        self.num_images_captured = 0
        self.num_events_reported = 0
        self.num_follow_spath = 0
        
        # Additional tracking for camera devices
        self.health_events = []
        self.suspicious_events = []
        self.last_activity = 0

    def add_hb(self, ts, neighbours, shortest_path, path_so_far, image_count, event_count):
        if ts not in self.all_hb_ts:
            self.hb_count = self.hb_count + 1
            self.all_hb_ts.append(ts)
            if shortest_path == path_so_far:
                self.num_follow_spath = self.num_follow_spath + 1
            if self.latest_hb_ts < ts:
                self.latest_hb_ts = ts
                self.neighbours = neighbours
                self.shortest_path = shortest_path
                self.num_images_captured = image_count
                self.num_events_reported = event_count
                self.paths_seen.append(path_so_far)
                self.last_activity = time.time()

    def add_camera_events(self, health_events: List, suspicious_events: List):
        """Add camera events from device"""
        self.health_events.extend(health_events)
        self.suspicious_events.extend(suspicious_events)

    def print_info(self):
        print(f"""AtCC Node {self.devid}:
                ---- Num HBs = {self.hb_count}
                ---- Latest HB = {self.latest_hb_ts}
                ---- HB Timestamps = {self.all_hb_ts}
                ---- Neighbours = {self.neighbours}
                ---- Shortest Path to CC = {self.shortest_path}
                ---- Actual Path to CC = {self.paths_seen}
                ---- Num HB Actually following Shortest Path to CC = {self.num_follow_spath}
                ---- Num images processed = {self.num_images_captured}
                ---- Num events reported = {self.num_events_reported}
                ---- Health Events = {len(self.health_events)}
                ---- Suspicious Events = {len(self.suspicious_events)}
                ---- Last Activity = {self.last_activity}
                """)

class CommandCentral:
    def __init__(self, devid: str, fcomm=None, ncomm=None, mission_id: str = "watchmen_surveillance"):
        self.devid = devid
        self.mission_id = mission_id
        self.neighbours_seen = []
        
        # COMMUNICATION DISABLED - ESP and other device communication not working  
        self.fcomm = None  # Disabled
        self.ncomm = None  # Disabled
        
        # if fcomm is None and ncomm is None:
        #     print("At least one communicator")
        #     return None
        # if fcomm is not None and ncomm is not None:
        #     print("At most one communicator")
        #     return None
        
        print(f"Command Central {devid} initialized in standalone mode (communication disabled)")
        
        # Node tracking
        self.node_list = {}  # Node : NodeInfo
        self.num_hbs_received = 0
        self.num_hbs_rerouted = 0
        
        # MQTT setup - only central device publishes
        self.setup_mqtt_writer()
        
        # Camera device registry for standalone operation
        self.registered_camera_devices = {}  # devid -> camera_object
        
    def setup_mqtt_writer(self):
        """Initialize MQTT writer for central device"""
        if QueueWriterJson is None:
            print("MQTT functionality not available")
            self.writer = None
            return
            
        try:
            self.writer = QueueWriterJson()
            print("MQTT writer initialized successfully for Command Central")
        except Exception as e:
            print(f"Failed to initialize MQTT writer: {e}")
            self.writer = None

    def register_camera_device(self, camera_device):
        """Register a camera device for event collection"""
        if camera_device and camera_device.camera:
            self.registered_camera_devices[camera_device.devid] = camera_device
            print(f"Registered camera device: {camera_device.devid}")

    def send_message(self, msg, dest=None):
        """Send message - DISABLED: Communication not working"""
        # COMMUNICATION DISABLED
        # if self.fcomm is not None:
        #     return self.fcomm.send_to_network(msg, self.devid, dest)
        # if self.ncomm is not None:
        #     msgstr = json.dumps(msg)
        #     return self.ncomm.send_message(msgstr, dest)
        
        print(f"[COMM DISABLED] Command Central would send to {dest}: {msg.get('mst', 'unknown_type')}")
        return False

    def console_output(self):
        """Display status of all nodes and publish activity summary"""
        print("\n" + "="*60)
        print("COMMAND CENTRAL STATUS REPORT")
        print("="*60)
        
        for n, info in self.node_list.items():
            info.print_info()
            
        print(f"\n ---- Rerouted {self.num_hbs_rerouted} out of {self.num_hbs_received} HBs")
        
        # Display camera device status
        print(f"\n ---- Registered Camera Devices: {len(self.registered_camera_devices)}")
        for devid, device in self.registered_camera_devices.items():
            if device.camera:
                print(f"     {devid}: {device.camera.image_count} images, {device.camera.detection_count} detections")
        
        # Collect and publish all events
        self.collect_and_publish_events()

    def collect_and_publish_events(self):
        """Collect events from all camera devices and publish via MQTT"""
        if not self.writer:
            print("MQTT not available - events collected but not published")
            return
            
        total_health_events = 0
        total_suspicious_events = 0
        
        # Collect events from all registered camera devices
        for devid, device in self.registered_camera_devices.items():
            if device.camera:
                events_data = device.camera.get_events_for_central()
                
                # Publish health events
                for health_event in events_data["health_events"]:
                    self._publish_health_event(health_event, devid)
                    total_health_events += 1
                
                # Publish suspicious events  
                for suspicious_event in events_data["suspicious_events"]:
                    self._publish_suspicious_event(suspicious_event, devid)
                    total_suspicious_events += 1
                
                # Clear events after publishing to avoid duplicates
                device.camera.health_events.clear()
                device.camera.suspicious_events.clear()
        
        # Publish overall activity summary
        self._publish_activity_summary(total_health_events, total_suspicious_events)
        
        print(f"Published {total_health_events} health events and {total_suspicious_events} suspicious events via MQTT")

    def _publish_health_event(self, health_event: Dict, device_id: str):
        """Publish health event via MQTT"""
        try:
            message_data = {
                "event_type": "health",
                "machine_id": device_id,
                "machine_name": f"Camera_{device_id}",
                "timestamp": health_event["timestamp"],
                "type": health_event["type"],
                "severity": health_event["severity"],
                "details": health_event.get("details", ""),
                "mission_id": self.mission_id,
                "reported_by": self.devid
            }
            
            success, error = self.writer.write_message(
                message_data=message_data,
                data_type="json",
                data_source="watchmen-health",
                destination_ids=["s3"],
                mission_id=self.mission_id,
                priority=2 if health_event["severity"] in ["high", "critical"] else 1
            )
            
            if success:
                print(f"Health event published for {device_id}: {health_event['type']}")
            else:
                print(f"Failed to publish health event for {device_id}: {error}")
                
        except Exception as e:
            print(f"MQTT health event publish failed for {device_id}: {e}")

    def _publish_suspicious_event(self, suspicious_event: Dict, device_id: str):
        """Publish suspicious event via MQTT"""
        try:
            message_data = {
                "event_type": "suspicious",
                "machine_id": device_id,
                "machine_name": f"Camera_{device_id}",
                "timestamp": suspicious_event["timestamp"],
                "type": suspicious_event["type"],
                "confidence": suspicious_event["confidence"],
                "image_url": suspicious_event["url"],
                "marked": suspicious_event["marked"],
                "details": suspicious_event.get("details", {}),
                "mission_id": self.mission_id,
                "reported_by": self.devid
            }
            
            success, error = self.writer.write_message(
                message_data=message_data,
                data_type="json",
                data_source="watchmen-suspicious",
                destination_ids=["s3"],
                mission_id=self.mission_id,
                priority=2  # High priority for suspicious events
            )
            
            if success:
                print(f"Suspicious event published for {device_id}: {suspicious_event['type']} (confidence: {suspicious_event['confidence']:.2f})")
            else:
                print(f"Failed to publish suspicious event for {device_id}: {error}")
                
        except Exception as e:
            print(f"MQTT suspicious event publish failed for {device_id}: {e}")

    def _publish_activity_summary(self, health_count: int, suspicious_count: int):
        """Publish activity summary via MQTT"""
        try:
            total_devices = len(self.registered_camera_devices)
            total_images = sum(device.camera.image_count for device in self.registered_camera_devices.values() if device.camera)
            total_detections = sum(device.camera.detection_count for device in self.registered_camera_devices.values() if device.camera)
            
            message_data = {
                "event_type": "network_activity_summary",
                "command_central_id": self.devid,
                "timestamp": datetime.now().isoformat(),
                "mission_id": self.mission_id,
                "network_stats": {
                    "total_camera_devices": total_devices,
                    "total_images_processed": total_images,
                    "total_detections_made": total_detections,
                    "health_events_published": health_count,
                    "suspicious_events_published": suspicious_count,
                    "nodes_tracked": len(self.node_list),
                    "heartbeats_received": self.num_hbs_received
                }
            }
            
            success, error = self.writer.write_message(
                message_data=message_data,
                data_type="json",
                data_source="watchmen-network",
                destination_ids=["s3"],
                mission_id=self.mission_id,
                priority=1
            )
            
            if success:
                print(f"Network activity summary published successfully")
            else:
                print(f"Failed to publish network activity summary: {error}")
                
        except Exception as e:
            print(f"MQTT network summary publish failed: {e}")

    def send_spath(self):
        """Send shortest path - DISABLED: Communication not working"""
        # COMMUNICATION DISABLED
        # for neighbour in self.neighbours_seen:
        #     ts = time.time_ns()
        #     spath_msg = {
        #             constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_SPATH,
        #             constants.JK_SOURCE : self.devid,
        #             constants.JK_DEST : neighbour,
        #             constants.JK_SOURCE_TIMESTAMP : ts,
        #             constants.JK_SHORTEST_PATH : [self.devid, neighbour],
        #             constants.JK_LAST_SENDER : self.devid,
        #             constants.JK_LAST_TS : ts,
        #         }
        #     self.send_message(spath_msg, neighbour)
        
        print(f"[COMM DISABLED] Would send shortest path to {len(self.neighbours_seen)} neighbours")
        return True

    def parse_hb_msg(self, msg):
        """Parse heartbeat message"""
        source = msg[constants.JK_SOURCE]
        dest = msg[constants.JK_DEST]
        source_ts = msg[constants.JK_SOURCE_TIMESTAMP]
        path_so_far = msg[constants.JK_PATH_SO_FAR] + [self.devid]
        msg_spath = msg[constants.JK_SHORTEST_PATH]
        neighbours = msg[constants.JK_NEIGHBOURS]
        image_count = msg[constants.JK_IMAGE_COUNT]
        event_count = msg[constants.JK_EVENT_COUNT]
        return (source, dest, source_ts, path_so_far, msg_spath, neighbours, image_count, event_count)

    def consume_hb(self, msg):
        """Consume heartbeat message"""
        hb_msg = self.parse_hb_msg(msg)
        (source, dest, source_ts, path_so_far, msg_spath, neighbours, image_count, event_count) = hb_msg
        if source not in self.node_list:
            self.node_list[source] = NodeInfo(source)
        info = self.node_list[source]
        info.add_hb(source_ts, neighbours, msg_spath, path_so_far, image_count, event_count)
        self.num_hbs_received = self.num_hbs_received + 1
        if path_so_far != msg_spath:
            self.num_hbs_rerouted = self.num_hbs_rerouted + 1
            print(f" --- At CC Noticed rerouting from {msg_spath} to {path_so_far}")

    def consume_image(self, msg):
        """Consume image message"""
        imf = f"/tmp/camera_captures_test/Image_CC_{msg['constants.JK_SOURCE']}_{msg['constants.JK_IMAGE_TS']}.jpg"
        print(f" %%%%%% ==== CC got an image from {msg['constants.JK_SOURCE']}, will save to {imf}")
        im = image.imstrtoimage(msg[constants.JK_IMAGE_DATA])
        im.save(imf)
        im.show()

    def process_msg(self, msg):
        """Process incoming messages"""
        mtype = msg[constants.JK_MESSAGE_TYPE]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg[constants.JK_SOURCE]
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
        if mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.consume_hb(msg)
        if mtype == constants.MESSAGE_TYPE_PHOTO:
            self.consume_image(msg)

    def run_standalone_monitoring(self, camera_devices: List, monitoring_interval: int = 300):
        """Run standalone monitoring with registered camera devices"""
        print(f"Starting standalone monitoring with {len(camera_devices)} camera devices")
        
        # Register all camera devices
        for device in camera_devices:
            self.register_camera_device(device)
        
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                print(f"\n{'='*60}")
                print(f"MONITORING CYCLE {cycle_count}")
                print(f"{'='*60}")
                
                # Trigger event checking on all camera devices
                for device in camera_devices:
                    if device.camera:
                        print(f"Triggering event check for device {device.devid}")
                        device.check_event()
                
                # Wait a bit for processing
                time.sleep(5)
                
                # Collect and publish events
                self.collect_and_publish_events()
                
                # Display status
                self.console_output()
                
                # Wait for next cycle
                print(f"\nWaiting {monitoring_interval} seconds before next cycle...")
                time.sleep(monitoring_interval)
                
        except KeyboardInterrupt:
            print("\nStandalone monitoring stopped by user")
        except Exception as e:
            print(f"Standalone monitoring failed: {e}")

    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.writer:
                self.writer.cleanup()
            print("Command Central cleaned up successfully")
        except Exception as e:
            print(f"Command Central cleanup failed: {e}")

def main():
    """Test command central"""
    print("Testing Command Central with MQTT Publishing")
    
    mission_id = "test_surveillance"
    cc = CommandCentral("CC", mission_id=mission_id)
    
    try:
        # Test MQTT publishing
        test_health_event = {
            "timestamp": datetime.now().isoformat(),
            "type": "hardware_failure",
            "severity": "high",
            "details": "Test health event"
        }
        
        test_suspicious_event = {
            "timestamp": datetime.now().isoformat(),
            "type": "human_detection",
            "confidence": 0.85,
            "url": "/tmp/test_image.jpg",
            "marked": "unreviewed",
            "details": {"test": True}
        }
        
        print("Testing MQTT event publishing...")
        cc._publish_health_event(test_health_event, "TEST_CAM_001")
        cc._publish_suspicious_event(test_suspicious_event, "TEST_CAM_001")
        cc._publish_activity_summary(1, 1)
        
        print("Command Central test completed")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        cc.cleanup()

if __name__=="__main__":
    main()