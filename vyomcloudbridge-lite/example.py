#!/usr/bin/env python3
"""
VyomCloudBridge Lite - Usage Examples
Demonstrates how to use the MicroPython-compatible MQTT bridge
"""

import json
import time
from message_handler import VyomCloudBridgeLite, MessageSender, MessageListener

def basic_usage_example():
    """Basic usage example with simple send and receive"""
    print("=== Basic Usage Example ===")
    
    # Configuration
    config = {
        "server": "localhost",  # Change to your MQTT broker
        "port": 1883,
        "client_id_prefix": "example-device",
        "machine_id": "test-machine-001",
        "user": None,  # Set if your broker requires authentication
        "password": None
    }
    
    # Initialize the bridge
    bridge = VyomCloudBridgeLite(config)
    
    # Send a message
    message = {
        "type": "sensor_data",
        "timestamp": int(time.time() * 1000),
        "data": {
            "temperature": 23.5,
            "humidity": 65.2,
            "pressure": 1013.25
        }
    }
    
    print("Sending sensor data...")
    success = bridge.send_message(message, "hq-server", "sensors")
    print(f"Send result: {'Success' if success else 'Failed'}")
    
    # Start listening
    print("Starting listener...")
    bridge.start_listening()
    
    # Run for a short time to demonstrate
    print("Running for 10 seconds...")
    for i in range(10):
        bridge.run_loop(1)
        
        # Send a heartbeat every 5 seconds
        if i % 5 == 0:
            heartbeat = {
                "type": "heartbeat",
                "timestamp": int(time.time() * 1000),
                "status": "online"
            }
            bridge.send_message(heartbeat, "hq-server", "system")
    
    # Cleanup
    bridge.cleanup()
    print("Basic example completed\n")

def sender_only_example():
    """Example using only the message sender"""
    print("=== Sender Only Example ===")
    
    sender = MessageSender(
        client_id="sender-example",
        server="localhost",
        port=1883
    )
    
    # Send multiple messages
    messages = [
        {"type": "log", "level": "info", "message": "System started"},
        {"type": "log", "level": "warning", "message": "Low battery warning"},
        {"type": "log", "level": "error", "message": "Sensor disconnected"}
    ]
    
    for msg in messages:
        success = sender.send_message(msg, "json", "logs", "log-server")
        print(f"Sent log message: {'✓' if success else '✗'}")
        time.sleep(1)
    
    sender.cleanup()
    print("Sender example completed\n")

def listener_only_example():
    """Example using only the message listener"""
    print("=== Listener Only Example ===")
    
    class CustomListener(MessageListener):
        def handle_message(self, message, data_source, source_id, topic):
            """Custom message handling"""
            print(f"\n🔔 Message received!")
            print(f"   From: {source_id}")
            print(f"   Source: {data_source}")
            print(f"   Topic: {topic}")
            
            # Parse message if it's JSON
            if isinstance(message, str):
                try:
                    parsed = json.loads(message)
                    print(f"   Data: {parsed}")
                    
                    # Example: Auto-respond to ping messages
                    if parsed.get("type") == "ping":
                        print("   🏓 Ping received, sending pong...")
                        # You would send response here if you had a sender
                        
                except json.JSONDecodeError:
                    print(f"   Raw: {message}")
            else:
                print(f"   Content: {message}")
    
    listener = CustomListener(
        client_id="listener-example",
        server="localhost",
        port=1883
    )
    
    # Subscribe to specific topics
    topics = [
        "vyom-mqtt-msg/test-machine-001/+/+/+",
        "test/ping"
    ]
    
    listener.start_listening(topics)
    
    print("Listening for messages for 15 seconds...")
    print("Send messages to topics: test/ping or vyom-mqtt-msg/test-machine-001/*/")
    
    for i in range(15):
        listener.check_messages()
        listener.process_messages()
        time.sleep(1)
    
    listener.cleanup()
    print("Listener example completed\n")

def ping_pong_example():
    """Example demonstrating ping-pong communication"""
    print("=== Ping-Pong Example ===")
    
    class PingPongBridge(VyomCloudBridgeLite):
        def __init__(self, config, is_pinger=False):
            super().__init__(config)
            self.is_pinger = is_pinger
            self.ping_count = 0
            
            # Override message handler
            self.listener.handle_message = self.handle_ping_pong
    
        def handle_ping_pong(self, message, data_source, source_id, topic):
            try:
                if isinstance(message, str):
                    msg_data = json.loads(message)
                else:
                    msg_data = message
                
                msg_type = msg_data.get("type")
                
                if msg_type == "ping":
                    print(f"🏓 Received PING from {source_id}")
                    # Send pong response
                    pong = {
                        "type": "pong",
                        "timestamp": int(time.time() * 1000),
                        "ping_id": msg_data.get("ping_id"),
                        "responder": self.machine_id
                    }
                    self.send_message(pong, source_id, "ping_pong")
                    print(f"🏓 Sent PONG to {source_id}")
                
                elif msg_type == "pong":
                    ping_id = msg_data.get("ping_id")
                    responder = msg_data.get("responder")
                    print(f"🎯 Received PONG from {responder} (ping_id: {ping_id})")
            
            except Exception as e:
                print(f"Error handling ping-pong: {e}")
        
        def send_ping(self, target_id):
            self.ping_count += 1
            ping = {
                "type": "ping",
                "timestamp": int(time.time() * 1000),
                "ping_id": self.ping_count,
                "sender": self.machine_id
            }
            success = self.send_message(ping, target_id, "ping_pong")
            if success:
                print(f"🏓 Sent PING #{self.ping_count} to {target_id}")
            return success
    
    # Create two devices for demo
    device1_config = {
        "server": "localhost",
        "port": 1883,
        "client_id_prefix": "ping-device",
        "machine_id": "device-001"
    }
    
    device2_config = {
        "server": "localhost",
        "port": 1883,
        "client_id_prefix": "pong-device", 
        "machine_id": "device-002"
    }
    
    device1 = PingPongBridge(device1_config, is_pinger=True)
    device2 = PingPongBridge(device2_config, is_pinger=False)
    
    # Start both listeners
    device1.start_listening()
    device2.start_listening()
    
    print("Starting ping-pong demo...")
    
    # Send pings from device1 to device2
    for i in range(3):
        device1.send_ping("device-002")
        
        # Process messages for both devices
        for _ in range(5):  # Give time for message exchange
            device1.run_loop(0.2)
            device2.run_loop(0.2)
            time.sleep(0.1)
        
        time.sleep(2)  # Wait between pings
    
    # Cleanup
    device1.cleanup()
    device2.cleanup()
    print("Ping-pong example completed\n")

def queue_example():
    """Example demonstrating filesystem queue functionality"""
    print("=== Queue Example ===")
    
    from filesystem_queue import FilesystemQueue
    
    # Create a test queue
    queue = FilesystemQueue("/tmp/test_queue", max_size=5)
    
    # Add some messages
    messages = [
        {"type": "data", "value": 100},
        {"type": "alert", "message": "High temperature"},
        {"type": "status", "online": True}
    ]
    
    print("Adding messages to queue...")
    for msg in messages:
        success = queue.enqueue(msg, f"topic_{msg['type']}")
        print(f"Enqueued {msg['type']}: {'✓' if success else '✗'}")
    
    print(f"Queue size: {queue.size()}")
    
    # Process messages
    print("\nProcessing messages...")
    while queue.size() > 0:
        item = queue.dequeue()
        if item:
            print(f"Processed: {item['message']} from {item['topic']}")
        time.sleep(0.5)
    
    print("Queue example completed\n")

def main():
    """Run all examples"""
    print("VyomCloudBridge Lite - Usage Examples")
    print("=" * 50)
    print()
    
    try:
        # Run examples
        basic_usage_example()
        time.sleep(1)
        
        sender_only_example()
        time.sleep(1)
        
        listener_only_example()
        time.sleep(1)
        
        ping_pong_example()
        time.sleep(1)
        
        queue_example()
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"Error running examples: {e}")
    
    print("All examples completed!")

if __name__ == "__main__":
    main()