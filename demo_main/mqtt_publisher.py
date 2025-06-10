import time
import os
from datetime import datetime, timezone
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson
from vyomcloudbridge.utils.configs import Configs
from vyomcloudbridge.utils.common import get_mission_upload_dir

class MQTTPublisher:
    def __init__(self, devid, mission_id="_all_"):
        self.devid = devid
        self.mission_id = mission_id
        self.writer = QueueWriterJson()
        
        # Get machine configuration
        self.machine_config = Configs.get_machine_config()
        self.machine_id = self.machine_config.get("machine_id", "-") or "-"
        self.organization_id = self.machine_config.get("organization_id", "-") or "-"
        
        print(f"Machine ID: {self.machine_id}")
        print(f"Organization ID: {self.organization_id}")

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
            
            success, error = self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-health",
                data_type="json",
                mission_id=self.mission_id,
                priority=priority,
                destination_ids=["s3"],
                merge_chunks=True
            )
            
            if success:
                print(f"Health event published for {machine_id}: {event_type} ({severity})")
                return True
            else:
                print(f"Error publishing health event for {machine_id}: {error}")
                return False
                
        except Exception as e:
            print(f"Error publishing health event for {machine_id}: {e}")
            return False

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
                merge_chunks=True
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
                destination_ids=["s3"],
                merge_chunks=True
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

    def publish_summary(self, stats_data):
        """Publish network summary"""
        try:
            epoch_ms = int(time.time() * 1000)
            
            message_data = {
                "timestamp": datetime.now().isoformat(),
                "machine_id": self.devid,
                **stats_data
            }
            
            filename = f"{epoch_ms}.json"
            
            success, error = self.writer.write_message(
                message_data=message_data,
                filename=filename,
                data_source="watchmen-summary",
                data_type="json",
                mission_id=self.mission_id,
                priority=1,
                destination_ids=["s3"],
                merge_chunks=True
            )
            
            if success:
                print(f"Summary published - Processed: {stats_data.get('images_processed_locally', 0)}, Events: {stats_data.get('events_detected_locally', 0)}")
                return True
            else:
                print(f"Error publishing summary: {error}")
                return False
                
        except Exception as e:
            print(f"Error publishing summary: {e}")
            return False

    def is_writer_healthy(self):
        """Check if MQTT writer is functioning"""
        try:
            return self.writer is not None
        except Exception:
            return False