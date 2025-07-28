#!/usr/bin/env python3
"""
VyomCloudBridge Lite - Main Client
MicroPython-compatible simplified client focusing on write_message functionality
"""

import json
import time
import gc
from filesystem_queue import FilesystemQueue

try:
    from umqtt.robust import MQTTClient
except ImportError:
    try:
        from umqtt.simple import MQTTClient
    except ImportError:
        try:
            from mock_umqtt import MQTTClient

            print("Warning: Using mock MQTT client for testing")
        except ImportError:
            print(
                "Error: umqtt library not found. Install micropython-umqtt.simple or micropython-umqtt.robust"
            )
            raise


class VyomClient:
    """
    Simplified VyomCloudBridge client for MicroPython
    Focuses on write_message functionality with same MQTT paths as original
    """

    def __init__(self, config):
        """
        Initialize VyomClient

        Args:
            config: Dictionary with configuration
                   {
                       "server": "mqtt.broker.com",
                       "port": 1883,
                       "machine_id": "device-001",
                       "organization_id": "20",
                       "user": "username",
                       "password": "password"
                   }
        """
        self.config = config
        self.machine_id = config.get("machine_id", "default-machine")
        self.organization_id = config.get("organization_id", "1")

        # MQTT client configuration
        client_id = f"machine{self.machine_id}Prod-writer"
        self.mqtt_client = MQTTClient(
            client_id=client_id,
            server=config["server"],
            port=config.get("port", 1883),
            user=config.get("user"),
            password=config.get("password"),
            keepalive=config.get("keepalive", 60),
        )

        # Connection state
        self.is_connected = False

        # Outgoing message queue for offline storage
        self.outgoing_queue = FilesystemQueue("/queue/outgoing", max_size=100)

        # Event handlers
        self.on_event_arrive = None
        self.on_hb_arrive = None
        self.on_image_arrive = None

        # Connect to broker
        self.connect()

    def connect(self, max_attempts=3):
        """Connect to MQTT broker"""
        for attempt in range(max_attempts):
            try:
                print(f"Connecting to MQTT broker... (attempt {attempt + 1})")
                self.mqtt_client.connect()
                self.is_connected = True
                print("Successfully connected to MQTT broker")

                # Process any queued messages
                self._process_queued_messages()
                return True

            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2 * (2**attempt))  # Exponential backoff

        print("Failed to connect to MQTT broker after all attempts")
        return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            if self.mqtt_client and self.is_connected:
                self.mqtt_client.disconnect()
                self.is_connected = False
                print("Disconnected from MQTT broker")
        except Exception as e:
            print(f"Error disconnecting: {e}")

    def _get_topic(self, dest_id, data_source, filename):
        """
        Generate MQTT topic using same format as original vyomcloudbridge
        Format: vyom-mqtt-msg/{dest_id}/{machine_id}/{data_source}/{filename}
        """
        return f"vyom-mqtt-msg/{dest_id}/{self.machine_id}/{data_source}/{filename}"

    def _generate_filename(self, data_type, custom_filename=None):
        """Generate filename with timestamp"""
        if custom_filename:
            return custom_filename

        epoch_ms = int(time.time() * 1000)

        if data_type == "json":
            return f"{epoch_ms}.json"
        elif data_type == "image":
            return f"{epoch_ms}.jpg"
        elif data_type == "binary":
            return f"{epoch_ms}.bin"
        else:
            return f"{epoch_ms}.{data_type}"

    def _prepare_message_data(self, message_data, data_type):
        """Prepare message data for sending"""
        if data_type == "json":
            if isinstance(message_data, dict):
                return json.dumps(message_data)
            elif isinstance(message_data, str):
                return message_data
            else:
                return json.dumps(message_data)
        elif data_type in ["image", "binary"]:
            # For binary data, return as-is if already bytes, otherwise encode
            if isinstance(message_data, bytes):
                return message_data
            elif isinstance(message_data, str):
                return message_data.encode("utf-8")
            else:
                return str(message_data).encode("utf-8")
        else:
            # Default to string conversion
            return str(message_data)

    def _publish_to_topic(self, topic, message_data):
        """Publish message to MQTT topic"""
        try:
            if not self.is_connected:
                return False

            self.mqtt_client.publish(topic, message_data)
            print(f"Published message to topic: {topic}")
            return True

        except Exception as e:
            print(f"Error publishing to {topic}: {e}")
            return False

    def _queue_message(
        self, message_data, data_type, data_source, destination_ids, filename
    ):
        """Queue message for later sending when connection is restored"""
        try:
            queue_item = {
                "message_data": message_data,
                "data_type": data_type,
                "data_source": data_source,
                "destination_ids": destination_ids,
                "filename": filename,
                "timestamp": int(time.time() * 1000),
            }

            success = self.outgoing_queue.enqueue(queue_item)
            if success:
                print(f"Message queued for later sending: {data_source}")
            return success

        except Exception as e:
            print(f"Error queuing message: {e}")
            return False

    def _process_queued_messages(self, max_process=10):
        """Process queued messages when connection is available"""
        if not self.is_connected:
            return 0

        processed = 0

        while processed < max_process:
            queue_item = self.outgoing_queue.dequeue()
            if not queue_item:
                break

            try:
                # Extract message details
                msg_data = queue_item["message"]
                message_data = msg_data["message_data"]
                data_type = msg_data["data_type"]
                data_source = msg_data["data_source"]
                destination_ids = msg_data["destination_ids"]
                filename = msg_data["filename"]

                # Retry sending
                success = self._send_message_direct(
                    message_data, data_type, data_source, destination_ids, filename
                )

                if not success:
                    # Put back in queue with failure tracking
                    self.outgoing_queue.mark_failed(queue_item)

                processed += 1

            except Exception as e:
                print(f"Error processing queued message: {e}")
                processed += 1

        gc.collect()
        return processed

    def _send_message_direct(
        self, message_data, data_type, data_source, destination_ids, filename
    ):
        """Send message directly without queuing"""
        try:
            # Prepare message data
            prepared_data = self._prepare_message_data(message_data, data_type)

            success_count = 0

            # Send to each destination
            for dest_id in destination_ids:
                # Generate topic using same format as original
                topic = self._get_topic(dest_id, data_source, filename)

                # Publish message
                if self._publish_to_topic(topic, prepared_data):
                    success_count += 1
                    print(f"Message sent to {dest_id} successfully")
                else:
                    print(f"Failed to send message to {dest_id}")

            return success_count > 0

        except Exception as e:
            print(f"Error in direct message send: {e}")
            return False

    def write_message(
        self,
        message_data,
        data_type,  # "json", "image", "binary"
        data_source,  # "telemetry", "camera1", "machine_state", etc.
        destination_ids,  # ["s3", "hq", "gcs_mqtt"]
        filename=None,
        mission_id=None,
        project_id=None,
        priority=1,
        send_live=False,
        background=False,
    ):
        """
        Main write_message function - compatible with original vyomcloudbridge API

        Args:
            message_data: The data to be sent (dict, str, bytes)
            data_type: Type of data ("json", "image", "binary")
            data_source: Source identifier ("telemetry", "camera1", "machine_state", etc.)
            destination_ids: List of destination IDs (["s3", "hq", "gcs_mqtt"])
            filename: Optional custom filename
            mission_id: Mission ID (for compatibility, not used in lite version)
            project_id: Project ID (for compatibility, not used in lite version)
            priority: Message priority (for compatibility, not used in lite version)
            send_live: Send as live data (not implemented in lite version)
            background: Send in background (not implemented in lite version)

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            # Generate filename if not provided
            if not filename:
                filename = self._generate_filename(data_type)

            # Validate inputs
            if not message_data:
                return False, "Message data cannot be empty"

            if not data_source:
                return False, "Data source cannot be empty"

            if not destination_ids or len(destination_ids) == 0:
                return False, "At least one destination ID must be provided"

            print(
                f"Sending {data_type} message from {data_source} to {destination_ids}"
            )

            # Try to send directly if connected
            if self.is_connected:
                success = self._send_message_direct(
                    message_data, data_type, data_source, destination_ids, filename
                )

                if success:
                    return True, None
                else:
                    # If direct send failed, queue for retry
                    queued = self._queue_message(
                        message_data, data_type, data_source, destination_ids, filename
                    )
                    if queued:
                        return True, "Message queued for retry"
                    else:
                        return False, "Failed to send and failed to queue message"
            else:
                # Not connected, queue the message
                queued = self._queue_message(
                    message_data, data_type, data_source, destination_ids, filename
                )
                if queued:
                    return True, "Message queued (not connected)"
                else:
                    return False, "Failed to queue message (not connected)"

        except Exception as e:
            error_msg = f"Error in write_message: {str(e)}"
            print(error_msg)
            return False, error_msg

    # Event handler methods
    def on_event_arrive(self, event_data):
        """
        Handle incoming event data
        Override this method to implement custom event handling

        Args:
            event_data: Event data received
        """
        if callable(self.on_event_arrive):
            try:
                self.on_event_arrive(event_data)
            except Exception as e:
                print(f"Error in event handler: {e}")
        else:
            print(f"Event arrived: {event_data}")

    def on_hb_arrive(self, heartbeat_data):
        """
        Handle incoming heartbeat data
        Override this method to implement custom heartbeat handling

        Args:
            heartbeat_data: Heartbeat data received
        """
        if callable(self.on_hb_arrive):
            try:
                self.on_hb_arrive(heartbeat_data)
            except Exception as e:
                print(f"Error in heartbeat handler: {e}")
        else:
            print(f"Heartbeat arrived: {heartbeat_data}")

    def on_image_arrive(self, image_data):
        """
        Handle incoming image data
        Override this method to implement custom image handling

        Args:
            image_data: Image data received
        """
        if callable(self.on_image_arrive):
            try:
                self.on_image_arrive(image_data)
            except Exception as e:
                print(f"Error in image handler: {e}")
        else:
            print(
                f"Image arrived: {len(image_data) if isinstance(image_data, (bytes, str)) else 'Unknown'} bytes"
            )

    # Utility methods
    def send_heartbeat(self, status="online", extra_data=None):
        """Send heartbeat message"""
        heartbeat = {
            "timestamp": int(time.time() * 1000),
            "machine_id": self.machine_id,
            "status": status,
            "organization_id": self.organization_id,
        }

        if extra_data:
            heartbeat.update(extra_data)

        return self.write_message(
            message_data=heartbeat,
            data_type="json",
            data_source="heartbeat",
            destination_ids=["s3", "hq"],
        )

    def send_telemetry(self, telemetry_data, destination_ids=None):
        """Send telemetry data"""
        if destination_ids is None:
            destination_ids = ["s3", "hq"]

        # Add timestamp if not present
        if isinstance(telemetry_data, dict) and "timestamp" not in telemetry_data:
            telemetry_data["timestamp"] = int(time.time() * 1000)

        return self.write_message(
            message_data=telemetry_data,
            data_type="json",
            data_source="telemetry",
            destination_ids=destination_ids,
        )

    def send_image(self, image_data, camera_id="camera1", destination_ids=None):
        """Send image data"""
        if destination_ids is None:
            destination_ids = ["s3"]

        filename = f"{int(time.time() * 1000)}.jpg"

        return self.write_message(
            message_data=image_data,
            data_type="image",
            data_source=camera_id,
            destination_ids=destination_ids,
            filename=filename,
        )

    def get_status(self):
        """Get client status"""
        return {
            "connected": self.is_connected,
            "machine_id": self.machine_id,
            "organization_id": self.organization_id,
            "queue_size": self.outgoing_queue.size(),
            "broker": f"{self.config['server']}:{self.config['port']}",
        }

    def cleanup(self):
        """Clean up resources"""
        try:
            self.disconnect()
            gc.collect()
            print("VyomClient cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {e}")


# Example usage and helper functions
def create_default_config():
    """Create default configuration for VyomClient"""
    return {
        "server": "localhost",
        "port": 1883,
        "machine_id": "micropython-device-001",
        "organization_id": "20",
        "user": None,
        "password": None,
        "keepalive": 60,
    }


def main():
    """Example usage of VyomClient"""
    print("VyomCloudBridge Lite Client Example")
    print("=" * 40)

    # Create client with default config
    config = create_default_config()
    client = VyomClient(config)

    try:
        # Send a test heartbeat
        print("\n1. Sending heartbeat...")
        success, error = client.send_heartbeat("online", {"test": True})
        print(f"Heartbeat result: {'Success' if success else f'Failed: {error}'}")

        # Send telemetry data
        print("\n2. Sending telemetry...")
        telemetry = {
            "temperature": 25.5,
            "humidity": 60.2,
            "battery": 85,
            "location": {"lat": 40.7128, "lon": -74.0060},
        }
        success, error = client.send_telemetry(telemetry)
        print(f"Telemetry result: {'Success' if success else f'Failed: {error}'}")

        # Send a custom message
        print("\n3. Sending custom message...")
        custom_data = {
            "event_type": "system_start",
            "message": "MicroPython device started",
            "version": "1.0",
        }
        success, error = client.write_message(
            message_data=custom_data,
            data_type="json",
            data_source="system_events",
            destination_ids=["s3", "hq"],
        )
        print(f"Custom message result: {'Success' if success else f'Failed: {error}'}")

        # Show status
        print("\n4. Client status:")
        status = client.get_status()
        for key, value in status.items():
            print(f"   {key}: {value}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.cleanup()


if __name__ == "__main__":
    main()
