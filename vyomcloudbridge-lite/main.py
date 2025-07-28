#!/usr/bin/env python3
"""
VyomCloudBridge Lite - Main Entry Point
MicroPython-compatible MQTT messaging bridge
"""

import json
import time
import sys
import gc
from message_handler import VyomCloudBridgeLite

def load_config(config_file="config.json"):
    """Load configuration from file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def create_default_config():
    """Create default configuration"""
    default_config = {
        "server": "localhost",
        "port": 1883,
        "client_id_prefix": "vyom-device",
        "machine_id": "default-machine",
        "user": None,
        "password": None,
        "topics": [
            "vyom-mqtt-msg/default-machine/+/+/+",
            "vyom-mqtt-msg/all/+/+/+"
        ],
        "loop_delay": 1,
        "auto_start": True
    }
    
    try:
        with open("config.json", 'w') as f:
            json.dump(default_config, f, indent=2)
        print("Created default config.json file")
    except Exception as e:
        print(f"Error creating config file: {e}")
    
    return default_config

def print_help():
    """Print help information"""
    print("\nVyomCloudBridge Lite - MicroPython MQTT Bridge")
    print("=" * 50)
    print("Usage: python main.py [options]")
    print("\nOptions:")
    print("  --help, -h          Show this help message")
    print("  --config FILE       Use specific config file (default: config.json)")
    print("  --send              Send a test message")
    print("  --listen            Listen for messages only")
    print("  --status            Show system status")
    print("  --create-config     Create default config.json file")
    print("\nConfig file format (JSON):")
    print("  {")
    print('    "server": "mqtt.broker.com",')
    print('    "port": 1883,')
    print('    "client_id_prefix": "vyom-device",')
    print('    "machine_id": "my-machine",')
    print('    "user": "username",')
    print('    "password": "password"')
    print("  }")
    print()

def send_test_message(bridge):
    """Send a test message"""
    test_message = {
        "timestamp": int(time.time() * 1000),
        "message": "Hello from VyomCloudBridge Lite!",
        "status": "test",
        "data": {
            "temperature": 25.5,
            "humidity": 60.2,
            "device_id": bridge.machine_id
        }
    }
    
    target_id = input("Enter target ID (or 'all' for broadcast): ").strip()
    if not target_id:
        target_id = "all"
    
    print(f"Sending test message to '{target_id}'...")
    success = bridge.send_message(test_message, target_id, "test_source")
    
    if success:
        print("✓ Test message sent successfully!")
    else:
        print("✗ Failed to send test message")
    
    return success

def show_status(bridge):
    """Show system status"""
    status = bridge.get_status()
    
    print("\nSystem Status")
    print("=" * 30)
    print(f"Sender Connected:    {'✓' if status['sender_connected'] else '✗'}")
    print(f"Listener Connected:  {'✓' if status['listener_connected'] else '✗'}")
    print(f"Is Running:          {'✓' if status['is_running'] else '✗'}")
    print(f"Outgoing Queue:      {status['sender_queue_status']['outgoing']} messages")
    print(f"Failed Queue:        {status['sender_queue_status']['failed']} messages")
    print(f"Incoming Queue:      {status['listener_queue_size']} messages")
    print(f"Subscribed Topics:   {status['sender_queue_status']['subscribed_topics']}")
    print()

def interactive_mode(bridge):
    """Run in interactive mode"""
    print("\nInteractive Mode - Commands:")
    print("  send    - Send a message")
    print("  status  - Show system status")
    print("  quit    - Exit program")
    print()
    
    bridge.start_listening()
    
    try:
        while True:
            command = input("vyom-lite> ").strip().lower()
            
            if command == "quit" or command == "exit":
                break
            elif command == "send":
                send_test_message(bridge)
            elif command == "status":
                show_status(bridge)
            elif command == "help":
                print("\nCommands: send, status, quit")
            else:
                if command:
                    print(f"Unknown command: {command}")
                
                # Process messages even when idle
                bridge.run_loop(0.1)
    
    except KeyboardInterrupt:
        print("\nInterrupt received...")
    
    finally:
        bridge.stop_listening()

def listen_mode(bridge, duration=None):
    """Run in listen-only mode"""
    print("Starting listener mode...")
    print("Press Ctrl+C to stop")
    
    bridge.start_listening()
    
    try:
        start_time = time.time()
        
        while True:
            bridge.run_loop()
            
            # Check duration limit
            if duration and (time.time() - start_time) > duration:
                print(f"Listening duration ({duration}s) reached")
                break
                
    except KeyboardInterrupt:
        print("\nStopping listener...")
    
    finally:
        bridge.stop_listening()

def main():
    """Main function"""
    config_file = "config.json"
    mode = "interactive"
    
    # Parse command line arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ["--help", "-h"]:
            print_help()
            return 0
        elif arg == "--config":
            if i + 1 < len(args):
                config_file = args[i + 1]
                i += 1
            else:
                print("Error: --config requires a filename")
                return 1
        elif arg == "--send":
            mode = "send"
        elif arg == "--listen":
            mode = "listen"
        elif arg == "--status":
            mode = "status"
        elif arg == "--create-config":
            create_default_config()
            return 0
        else:
            print(f"Unknown argument: {arg}")
            print("Use --help for usage information")
            return 1
        
        i += 1
    
    # Load configuration
    config = load_config(config_file)
    if not config:
        print(f"Config file '{config_file}' not found or invalid.")
        print("Creating default configuration...")
        config = create_default_config()
    
    print(f"Connecting to MQTT broker: {config['server']}:{config['port']}")
    print(f"Machine ID: {config['machine_id']}")
    
    # Initialize bridge
    try:
        bridge = VyomCloudBridgeLite(config)
    except Exception as e:
        print(f"Error initializing bridge: {e}")
        return 1
    
    # Run based on mode
    try:
        if mode == "send":
            if not send_test_message(bridge):
                return 1
        elif mode == "listen":
            listen_mode(bridge)
        elif mode == "status":
            show_status(bridge)
        else:  # interactive mode
            interactive_mode(bridge)
    
    except Exception as e:
        print(f"Error in main loop: {e}")
        return 1
    
    finally:
        print("Cleaning up...")
        bridge.cleanup()
        gc.collect()
    
    return 0

# Custom message handler example
class CustomMessageHandler(VyomCloudBridgeLite):
    """
    Example of extending VyomCloudBridgeLite with custom message handling
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Override the listener's message handler
        self.listener.handle_message = self.custom_message_handler
    
    def custom_message_handler(self, message, data_source, source_id, topic):
        """Custom message processing logic"""
        try:
            print(f"\n--- Custom Message Handler ---")
            print(f"From: {source_id}")
            print(f"Source: {data_source}")
            print(f"Topic: {topic}")
            
            # Try to parse JSON message
            if isinstance(message, str):
                try:
                    parsed_message = json.loads(message)
                    print(f"Parsed Message: {parsed_message}")
                    
                    # Example: respond to ping messages
                    if parsed_message.get("type") == "ping":
                        response = {
                            "type": "pong",
                            "timestamp": int(time.time() * 1000),
                            "original_sender": source_id,
                            "responder": self.machine_id
                        }
                        self.send_message(response, source_id, "ping_response")
                        print("Sent pong response")
                    
                except json.JSONDecodeError:
                    print(f"Raw Message: {message}")
            else:
                print(f"Message: {message}")
            
            print("-" * 30)
            
        except Exception as e:
            print(f"Error in custom message handler: {e}")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)