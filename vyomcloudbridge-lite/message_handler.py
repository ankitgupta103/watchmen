import json
import time
import gc
from mqtt_client import VyomMqttClient
from filesystem_queue import FilesystemQueue

class MessageSender:
    """
    MicroPython-compatible message sender
    Simplified version of AwsiotMqttSender
    """
    
    def __init__(self, client_id, server, port=1883, user=None, password=None):
        self.client_id = client_id
        self.server = server
        self.machine_id = None
        
        # Initialize MQTT client
        self.mqtt_client = VyomMqttClient(
            client_id=client_id,
            server=server,
            port=port,
            user=user,
            password=password
        )
        
        # Load machine config if available
        self._load_machine_config()
        
        # Connect to broker
        self.is_connected = False
        self.connect()
    
    def _load_machine_config(self):
        """Load machine configuration from file"""
        try:
            # Try to read from the constants file or config
            import constants
            # This would typically load from a config file
            self.machine_id = "default-machine"  # Fallback
        except:
            self.machine_id = "default-machine"
    
    def connect(self):
        """Connect to MQTT broker"""
        self.is_connected = self.mqtt_client.connect()
        return self.is_connected
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.mqtt_client.disconnect()
        self.is_connected = False
    
    def send_message(self, message, message_type, data_source, target_id, topic=None):
        """
        Send message to target
        
        Args:
            message: Message content (string or dict)
            message_type: Type of message (e.g., 'json', 'text')
            data_source: Source of the data
            target_id: Target destination ID
            topic: Optional custom topic
        """
        try:
            # Generate topic if not provided
            if not topic:
                timestamp = int(time.time() * 1000)
                filename = f"{data_source}_{timestamp}.json"
                topic = f"vyom-mqtt-msg/{target_id}/{self.machine_id}/{data_source}/{filename}"
            
            # Ensure message is string
            if isinstance(message, dict):
                message = json.dumps(message)
            elif not isinstance(message, str):
                message = str(message)
            
            # Send message
            success = self.mqtt_client.publish(topic, message)
            
            # Process any queued messages
            self.mqtt_client.process_queued_messages()
            
            return success
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        self.mqtt_client.cleanup()


class MessageListener:
    """
    MicroPython-compatible message listener
    Simplified version of AwsiotMqttListener
    """
    
    def __init__(self, client_id, server, port=1883, user=None, password=None):
        self.client_id = client_id
        self.server = server
        self.machine_id = None
        self.is_running = False
        
        # Message processing queue
        self.message_queue = FilesystemQueue("/queue/incoming", max_size=30)
        
        # Initialize MQTT client
        self.mqtt_client = VyomMqttClient(
            client_id=client_id,
            server=server,
            port=port,
            user=user,
            password=password
        )
        
        # Set default message callback
        self.mqtt_client.set_default_callback(self._on_message_received)
        
        # Load machine config
        self._load_machine_config()
        
        # Connect to broker
        self.is_connected = False
        self.connect()
    
    def _load_machine_config(self):
        """Load machine configuration"""
        try:
            import constants
            self.machine_id = "default-machine"  # Fallback
        except:
            self.machine_id = "default-machine"
    
    def connect(self):
        """Connect to MQTT broker"""
        self.is_connected = self.mqtt_client.connect()
        return self.is_connected
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.mqtt_client.disconnect()
        self.is_connected = False
    
    def _on_message_received(self, topic, message):
        """Handle incoming MQTT messages"""
        try:
            print(f"Received message on topic: {topic}")
            
            # Parse topic to extract information
            # Expected format: vyom-mqtt-msg/{machine_id}/{source}/{data_source}/{filename}
            topic_parts = topic.split("/")
            
            if len(topic_parts) >= 4:
                target_machine_id = topic_parts[1]
                source_id = topic_parts[2]
                data_source = topic_parts[3]
                
                # Process message if it's for this machine
                if target_machine_id == self.machine_id or target_machine_id == "all":
                    self.handle_message(message, data_source, source_id, topic)
            
            gc.collect()
            
        except Exception as e:
            print(f"Error processing received message: {e}")
    
    def handle_message(self, message, data_source, source_id, topic):
        """
        Handle processed message - override this method in subclasses
        
        Args:
            message: Parsed message content
            data_source: Source of the data
            source_id: ID of the message source
            topic: Full MQTT topic
        """
        try:
            print(f"Processing message from {source_id}/{data_source}")
            print(f"Message: {message}")
            
            # Queue message for processing
            self.message_queue.enqueue({
                "message": message,
                "data_source": data_source,
                "source_id": source_id,
                "topic": topic,
                "received_at": int(time.time() * 1000)
            })
            
        except Exception as e:
            print(f"Error handling message: {e}")
    
    def subscribe_to_topics(self, topics):
        """Subscribe to multiple topics"""
        success_count = 0
        for topic in topics:
            if self.mqtt_client.subscribe(topic):
                success_count += 1
        
        return success_count == len(topics)
    
    def start_listening(self, topics=None):
        """Start listening for messages"""
        try:
            self.is_running = True
            
            # Subscribe to default topics if none provided
            if not topics:
                topics = [
                    f"vyom-mqtt-msg/{self.machine_id}/+/+/+",
                    f"vyom-mqtt-msg/all/+/+/+"
                ]
            
            # Subscribe to topics
            for topic in topics:
                self.mqtt_client.subscribe(topic)
                print(f"Subscribed to topic: {topic}")
            
            print("Listening for messages...")
            
        except Exception as e:
            print(f"Error starting listener: {e}")
            self.is_running = False
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.is_running = False
        print("Stopped listening for messages")
    
    def process_messages(self, max_messages=5):
        """Process queued messages"""
        processed = 0
        
        while processed < max_messages:
            queue_item = self.message_queue.dequeue()
            if not queue_item:
                break
            
            try:
                # Process the message (override this in subclasses)
                self._process_queued_message(queue_item)
                processed += 1
            except Exception as e:
                print(f"Error processing queued message: {e}")
                # Put message back in queue with failure tracking
                self.message_queue.mark_failed(queue_item)
        
        gc.collect()
        return processed
    
    def _process_queued_message(self, queue_item):
        """Process a single queued message - override in subclasses"""
        msg_data = queue_item["message"]
        print(f"Processing queued message: {msg_data}")
        # Default implementation just prints the message
    
    def check_messages(self):
        """Check for new messages (non-blocking)"""
        if self.is_connected:
            self.mqtt_client.check_messages()
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_listening()
        self.mqtt_client.cleanup()


class VyomCloudBridgeLite:
    """
    Main class for vyomcloudbridge-lite
    Combines sender and listener functionality
    """
    
    def __init__(self, config):
        """
        Initialize with configuration
        
        Args:
            config: Dictionary with MQTT connection details
                   {
                       "server": "mqtt.broker.com",
                       "port": 1883,
                       "client_id_prefix": "vyom-device",
                       "user": "username",
                       "password": "password"
                   }
        """
        self.config = config
        self.machine_id = config.get("machine_id", "default-machine")
        
        # Initialize sender and listener with different client IDs
        sender_id = f"{config['client_id_prefix']}-sender-{self.machine_id}"
        listener_id = f"{config['client_id_prefix']}-listener-{self.machine_id}"
        
        self.sender = MessageSender(
            client_id=sender_id,
            server=config["server"],
            port=config.get("port", 1883),
            user=config.get("user"),
            password=config.get("password")
        )
        
        self.listener = MessageListener(
            client_id=listener_id,
            server=config["server"],
            port=config.get("port", 1883),
            user=config.get("user"),
            password=config.get("password")
        )
        
        self.is_running = False
    
    def send_message(self, message, target_id, data_source="default", message_type="json"):
        """Send message using the sender"""
        return self.sender.send_message(message, message_type, data_source, target_id)
    
    def start_listening(self, topics=None):
        """Start the message listener"""
        self.listener.start_listening(topics)
        self.is_running = True
    
    def stop_listening(self):
        """Stop the message listener"""
        self.listener.stop_listening()
        self.is_running = False
    
    def run_loop(self, loop_delay=1):
        """
        Main processing loop
        Call this regularly to process messages
        """
        try:
            # Check for incoming messages
            self.listener.check_messages()
            
            # Process queued messages
            self.listener.process_messages()
            
            # Process outgoing message queue
            self.sender.mqtt_client.process_queued_messages()
            
            # Small delay to prevent busy waiting
            time.sleep(loop_delay)
            
            gc.collect()
            
        except Exception as e:
            print(f"Error in main loop: {e}")
    
    def get_status(self):
        """Get system status"""
        return {
            "sender_connected": self.sender.is_connected,
            "listener_connected": self.listener.is_connected,
            "is_running": self.is_running,
            "sender_queue_status": self.sender.mqtt_client.get_queue_status(),
            "listener_queue_size": self.listener.message_queue.size()
        }
    
    def cleanup(self):
        """Clean up all resources"""
        self.stop_listening()
        self.sender.cleanup()
        self.listener.cleanup()