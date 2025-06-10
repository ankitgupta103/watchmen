import time
import os

class HealthMonitor:
    def __init__(self, devid, mqtt_publisher, image_processor, health_check_interval=60):
        self.devid = devid
        self.mqtt_publisher = mqtt_publisher
        self.image_processor = image_processor
        self.health_check_interval = health_check_interval
        self.last_health_check = 0
        self.system_start_time = time.time()

    def check_system_health(self, images_processed=0):
        """Check system health and publish health events every 60 seconds"""
        current_time = time.time()
        
        if current_time - self.last_health_check >= self.health_check_interval:
            self.last_health_check = current_time
            
            # Check AI detector health
            self._check_ai_detector_health()
            
            # Check image directory health
            self._check_image_directory_health()
            
            # Check MQTT writer health
            self._check_mqtt_health()
            
            # System uptime health check
            self._check_system_uptime(images_processed)

    def _check_ai_detector_health(self):
        """Check AI detector health"""
        try:
            if self.image_processor.is_detector_healthy():
                self.mqtt_publisher.publish_health_event(
                    self.devid,
                    "camera_failure",  # Camera system includes AI
                    "low",
                    "AI detector operational"
                )
            else:
                self.mqtt_publisher.publish_health_event(
                    self.devid,
                    "camera_failure",
                    "high",
                    "AI detector not available"
                )
        except Exception as e:
            self.mqtt_publisher.publish_health_event(
                self.devid,
                "camera_failure",
                "critical",
                f"AI detector error: {str(e)}"
            )

    def _check_image_directory_health(self):
        """Check image directory accessibility"""
        try:
            if os.path.exists(self.image_processor.image_directory):
                available_images = len(self.image_processor.get_image_files())
                self.mqtt_publisher.publish_health_event(
                    self.devid,
                    "hardware_failure",
                    "low", 
                    f"Image directory accessible - {available_images} images available"
                )
            else:
                self.mqtt_publisher.publish_health_event(
                    self.devid,
                    "hardware_failure",
                    "medium",
                    "Image directory not accessible"
                )
        except Exception as e:
            self.mqtt_publisher.publish_health_event(
                self.devid,
                "hardware_failure",
                "high",
                f"Image directory check failed: {str(e)}"
            )

    def _check_mqtt_health(self):
        """Check MQTT connection health"""
        try:
            if self.mqtt_publisher.is_writer_healthy():
                self.mqtt_publisher.publish_health_event(
                    self.devid,
                    "offline",
                    "low",
                    "MQTT connection operational"
                )
            else:
                self.mqtt_publisher.publish_health_event(
                    self.devid,
                    "offline", 
                    "high",
                    "MQTT writer not available"
                )
        except Exception as e:
            self.mqtt_publisher.publish_health_event(
                self.devid,
                "offline",
                "critical",
                f"MQTT connection error: {str(e)}"
            )

    def _check_system_uptime(self, images_processed):
        """Check system uptime and performance"""
        try:
            uptime_hours = (time.time() - self.system_start_time) / 3600
            self.mqtt_publisher.publish_health_event(
                self.devid,
                "hardware_failure",
                "low",
                f"System uptime: {uptime_hours:.1f} hours, Images processed: {images_processed}"
            )
        except Exception as e:
            self.mqtt_publisher.publish_health_event(
                self.devid,
                "hardware_failure",
                "medium",
                f"System monitoring error: {str(e)}"
            )

    def log_health_status(self):
        """Log health status locally (for devices without MQTT)"""
        current_time = time.time()
        
        if current_time - self.last_health_check >= self.health_check_interval:
            self.last_health_check = current_time
            
            print(f"🏥 Performing health check for device {self.devid}")
            
            # AI detector health
            if self.image_processor.is_detector_healthy():
                print(f"🏥 Health: AI detector operational")
            else:
                print(f"🏥 Health: AI detector not available (HIGH severity)")
            
            # Image directory health
            if os.path.exists(self.image_processor.image_directory):
                available_images = len(self.image_processor.get_image_files())
                print(f"🏥 Health: Image directory accessible - {available_images} images")
            else:
                print(f"🏥 Health: Image directory not accessible (MEDIUM severity)")
            
            # System uptime
            uptime_hours = (current_time - self.system_start_time) / 3600
            print(f"🏥 Health: Uptime {uptime_hours:.1f}h")

    def get_uptime_hours(self):
        """Get system uptime in hours"""
        return (time.time() - self.system_start_time) / 3600