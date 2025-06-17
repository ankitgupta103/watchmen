from typing import Dict
from datetime import datetime

class CenrtralReporter:
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
                priority=1 if health_event["severity"] in ["high", "critical"] else 1
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
                priority=3  # High priority for suspicious events
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
