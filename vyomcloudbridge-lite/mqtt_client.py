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
            # Try to use mock for testing
            from mock_umqtt import MQTTClient
            print("Warning: Using mock MQTT client for testing")
        except ImportError:
            print("Error: umqtt library not found. Install micropython-umqtt.simple or micropython-umqtt.robust")
            raise

class VyomMqttClient:
    """
    MicroPython-compatible MQTT client for vyomcloudbridge-lite
    Simplified version without AWS IoT SDK dependencies
    """
    
    def __init__(self, client_id, server, port=1883, user=None, password=None, 
                 keepalive=60, ssl=False, ssl_params=None):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.keepalive = keepalive
        self.ssl = ssl
        self.ssl_params = ssl_params or {}
        
        # Connection state
        self.is_connected = False
        self.subscribed_topics = set()
        
        # Message handling
        self.message_callbacks = {}
        self.default_callback = None
        
        # Queue for outgoing messages
        self.outgoing_queue = FilesystemQueue("/queue/outgoing", max_size=50)
        # Queue for failed messages
        self.failed_queue = FilesystemQueue("/queue/failed", max_size=20)
        
        # Initialize MQTT client
        self.mqtt_client = None
        self._init_mqtt_client()
    
    def _init_mqtt_client(self):
        """Initialize the MQTT client"""
        try:
            self.mqtt_client = MQTTClient(
                client_id=self.client_id,
                server=self.server,
                port=self.port,
                user=self.user,
                password=self.password,
                keepalive=self.keepalive,
                ssl=self.ssl,
                ssl_params=self.ssl_params
            )
            
            # Set callback for incoming messages
            self.mqtt_client.set_callback(self._on_message)
            
        except Exception as e:
            print(f"Error initializing MQTT client: {e}")
            raise
    
    def _on_message(self, topic, msg):
        """Handle incoming MQTT messages"""
        try:
            topic_str = topic.decode('utf-8')
            msg_str = msg.decode('utf-8')
            
            print(f"Received message on topic: {topic_str}")
            
            # Try to parse JSON message
            try:
                parsed_msg = json.loads(msg_str)
            except:
                parsed_msg = msg_str
            
            # Call specific topic callback if exists
            if topic_str in self.message_callbacks:
                self.message_callbacks[topic_str](topic_str, parsed_msg)
            elif self.default_callback:
                self.default_callback(topic_str, parsed_msg)
            
            gc.collect()
            
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def connect(self, max_attempts=3, delay=2):
        """Connect to MQTT broker with retry logic"""
        for attempt in range(max_attempts):
            try:
                print(f"Connecting to MQTT broker... (attempt {attempt + 1})")
                self.mqtt_client.connect()
                self.is_connected = True
                print("Successfully connected to MQTT broker")
                
                # Resubscribe to topics if any
                self._resubscribe_all()
                return True
                
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
        
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
    
    def subscribe(self, topic, callback=None, qos=0):
        """Subscribe to a topic"""
        try:
            if not self.is_connected:
                print("Not connected to MQTT broker")
                return False
            
            self.mqtt_client.subscribe(topic, qos)
            self.subscribed_topics.add(topic)
            
            if callback:
                self.message_callbacks[topic] = callback
            
            print(f"Subscribed to topic: {topic}")
            return True
            
        except Exception as e:
            print(f"Error subscribing to {topic}: {e}")
            return False
    
    def unsubscribe(self, topic):
        """Unsubscribe from a topic"""
        try:
            if not self.is_connected:
                return False
            
            self.mqtt_client.unsubscribe(topic)
            self.subscribed_topics.discard(topic)
            self.message_callbacks.pop(topic, None)
            
            print(f"Unsubscribed from topic: {topic}")
            return True
            
        except Exception as e:
            print(f"Error unsubscribing from {topic}: {e}")
            return False
    
    def _resubscribe_all(self):
        """Resubscribe to all topics after reconnection"""
        for topic in self.subscribed_topics.copy():
            try:
                self.mqtt_client.subscribe(topic)
                print(f"Resubscribed to topic: {topic}")
            except Exception as e:
                print(f"Failed to resubscribe to {topic}: {e}")
    
    def publish(self, topic, message, qos=0, retain=False):
        """Publish message to topic"""
        try:
            if not self.is_connected:
                print("Not connected, queuing message...")
                self.outgoing_queue.enqueue({
                    "topic": topic,
                    "message": message,
                    "qos": qos,
                    "retain": retain
                })
                return False
            
            # Convert message to string if it's not already
            if isinstance(message, dict):
                message = json.dumps(message)
            elif not isinstance(message, str):
                message = str(message)
            
            self.mqtt_client.publish(topic, message, qos=qos, retain=retain)
            print(f"Published message to topic: {topic}")
            return True
            
        except Exception as e:
            print(f"Error publishing to {topic}: {e}")
            # Queue failed message for retry
            self.failed_queue.enqueue({
                "topic": topic,
                "message": message,
                "qos": qos,
                "retain": retain,
                "error": str(e)
            })
            return False
    
    def process_queued_messages(self):
        """Process queued outgoing messages"""
        if not self.is_connected:
            return
        
        processed = 0
        max_process = 10  # Limit to prevent blocking
        
        while processed < max_process:
            queue_item = self.outgoing_queue.dequeue()
            if not queue_item:
                break
            
            msg_data = queue_item["message"]
            success = self.publish(
                msg_data["topic"],
                msg_data["message"],
                msg_data.get("qos", 0),
                msg_data.get("retain", False)
            )
            
            if not success:
                # Put back in queue with attempt counter
                self.outgoing_queue.mark_failed(queue_item)
            
            processed += 1
        
        gc.collect()
    
    def check_messages(self, timeout=1000):
        """Check for incoming messages (non-blocking)"""
        try:
            if self.is_connected:
                self.mqtt_client.check_msg()
        except Exception as e:
            print(f"Error checking messages: {e}")
            self.is_connected = False
    
    def wait_msg(self):
        """Wait for incoming message (blocking)"""
        try:
            if self.is_connected:
                self.mqtt_client.wait_msg()
        except Exception as e:
            print(f"Error waiting for message: {e}")
            self.is_connected = False
    
    def set_default_callback(self, callback):
        """Set default callback for messages without specific handlers"""
        self.default_callback = callback
    
    def ping(self):
        """Send ping to broker"""
        try:
            if self.is_connected:
                self.mqtt_client.ping()
                return True
        except Exception as e:
            print(f"Ping failed: {e}")
            self.is_connected = False
        return False
    
    def get_queue_status(self):
        """Get status of message queues"""
        return {
            "outgoing": self.outgoing_queue.size(),
            "failed": self.failed_queue.size(),
            "connected": self.is_connected,
            "subscribed_topics": len(self.subscribed_topics)
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.disconnect()
        gc.collect()