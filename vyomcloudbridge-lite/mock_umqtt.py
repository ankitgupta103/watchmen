"""
Mock umqtt module for testing purposes
Provides basic MQTT client interface for testing without actual umqtt library
"""

class MQTTClient:
    """Mock MQTT client for testing"""
    
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
        
        self.is_connected = False
        self.callback = None
        self.subscribed_topics = set()
        
        print(f"Mock MQTT Client created: {client_id}@{server}:{port}")
    
    def set_callback(self, callback):
        """Set message callback"""
        self.callback = callback
    
    def connect(self):
        """Mock connect"""
        self.is_connected = True
        print(f"Mock MQTT: Connected to {self.server}:{self.port}")
    
    def disconnect(self):
        """Mock disconnect"""
        self.is_connected = False
        print("Mock MQTT: Disconnected")
    
    def subscribe(self, topic, qos=0):
        """Mock subscribe"""
        self.subscribed_topics.add(topic)
        print(f"Mock MQTT: Subscribed to {topic}")
    
    def unsubscribe(self, topic):
        """Mock unsubscribe"""
        self.subscribed_topics.discard(topic)
        print(f"Mock MQTT: Unsubscribed from {topic}")
    
    def publish(self, topic, message, qos=0, retain=False):
        """Mock publish"""
        print(f"Mock MQTT: Published to {topic}: {message[:50]}...")
    
    def check_msg(self):
        """Mock check message"""
        pass
    
    def wait_msg(self):
        """Mock wait message"""
        pass
    
    def ping(self):
        """Mock ping"""
        print("Mock MQTT: Ping sent")

# Mock the module structure
class MockSimple:
    MQTTClient = MQTTClient

class MockRobust:
    MQTTClient = MQTTClient

# Create mock modules
simple = MockSimple()
robust = MockRobust()