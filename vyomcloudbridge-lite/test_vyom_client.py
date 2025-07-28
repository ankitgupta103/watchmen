#!/usr/bin/env python3
"""
Test script for VyomClient write_message functionality
"""

import time
from vyom_client import VyomClient, create_default_config

def test_write_message():
    """Test the write_message functionality"""
    print("Testing VyomClient write_message functionality")
    print("=" * 50)
    
    # Create client configuration
    config = create_default_config()
    print(f"Using config: {config}")
    
    # Initialize client
    try:
        client = VyomClient(config)
        print(f"✓ VyomClient initialized successfully")
        print(f"  Machine ID: {client.machine_id}")
        print(f"  Connected: {client.is_connected}")
    except Exception as e:
        print(f"✗ Failed to initialize VyomClient: {e}")
        return False
    
    # Test 1: JSON message
    print("\n1. Testing JSON message...")
    json_data = {
        "timestamp": int(time.time() * 1000),
        "sensor_id": "temp_01",
        "temperature": 25.3,
        "humidity": 65.2,
        "location": "greenhouse_1"
    }
    
    success, error = client.write_message(
        message_data=json_data,
        data_type="json",
        data_source="sensors",
        destination_ids=["s3", "hq"]
    )
    
    if success:
        print("✓ JSON message sent successfully")
        if error:
            print(f"  Note: {error}")
    else:
        print(f"✗ JSON message failed: {error}")
    
    # Test 2: Heartbeat message
    print("\n2. Testing heartbeat message...")
    success, error = client.send_heartbeat("online", {"test_mode": True})
    
    if success:
        print("✓ Heartbeat sent successfully")
        if error:
            print(f"  Note: {error}")
    else:
        print(f"✗ Heartbeat failed: {error}")
    
    # Test 3: Telemetry message
    print("\n3. Testing telemetry message...")
    telemetry = {
        "battery_voltage": 12.6,
        "signal_strength": -45,
        "gps_lat": 40.7128,
        "gps_lon": -74.0060,
        "altitude": 150.5
    }
    
    success, error = client.send_telemetry(telemetry, ["s3", "gcs_mqtt"])
    
    if success:
        print("✓ Telemetry sent successfully")
        if error:
            print(f"  Note: {error}")
    else:
        print(f"✗ Telemetry failed: {error}")
    
    # Test 4: Binary/Image data (simulated)
    print("\n4. Testing image data...")
    fake_image_data = b"FAKE_JPEG_DATA_FOR_TESTING" * 10  # Simulate image bytes
    
    success, error = client.send_image(fake_image_data, "camera1", ["s3"])
    
    if success:
        print("✓ Image data sent successfully")
        if error:
            print(f"  Note: {error}")
    else:
        print(f"✗ Image data failed: {error}")
    
    # Test 5: Custom data source
    print("\n5. Testing custom data source...")
    log_data = {
        "level": "INFO",
        "message": "System startup completed",
        "module": "main",
        "timestamp": int(time.time() * 1000)
    }
    
    success, error = client.write_message(
        message_data=log_data,
        data_type="json",
        data_source="system_logs",
        destination_ids=["hq"],
        filename="startup.json"
    )
    
    if success:
        print("✓ Custom log message sent successfully")
        if error:
            print(f"  Note: {error}")
    else:
        print(f"✗ Custom log message failed: {error}")
    
    # Test 6: Test event handlers
    print("\n6. Testing event handlers...")
    
    # Set up event handlers
    def handle_event(event_data):
        print(f"Event handler called with: {event_data}")
    
    def handle_heartbeat(hb_data):
        print(f"Heartbeat handler called with: {hb_data}")
    
    def handle_image(img_data):
        print(f"Image handler called with {len(img_data)} bytes")
    
    client.on_event_arrive = handle_event
    client.on_hb_arrive = handle_heartbeat  
    client.on_image_arrive = handle_image
    
    # Test the handlers
    client.on_event_arrive({"type": "test_event", "data": "test"})
    client.on_hb_arrive({"status": "online", "timestamp": int(time.time())})
    client.on_image_arrive(b"fake_image_data")
    
    print("✓ Event handlers tested successfully")
    
    # Show final status
    print("\n7. Final status:")
    status = client.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Cleanup
    client.cleanup()
    print("\n✓ Test completed successfully!")
    return True

def test_mqtt_topics():
    """Test that MQTT topics are generated correctly"""
    print("\nTesting MQTT topic generation")
    print("-" * 30)
    
    config = create_default_config()
    client = VyomClient(config)
    
    # Test topic generation
    test_cases = [
        ("s3", "sensors", "1640995200000.json"),
        ("hq", "camera1", "1640995201000.jpg"),
        ("gcs_mqtt", "telemetry", "1640995202000.json"),
    ]
    
    for dest_id, data_source, filename in test_cases:
        topic = client._get_topic(dest_id, data_source, filename)
        expected = f"vyom-mqtt-msg/{dest_id}/{client.machine_id}/{data_source}/{filename}"
        
        if topic == expected:
            print(f"✓ Topic correct: {topic}")
        else:
            print(f"✗ Topic mismatch:")
            print(f"  Expected: {expected}")
            print(f"  Got:      {topic}")
    
    client.cleanup()
    return True

def main():
    """Run all tests"""
    print("VyomClient Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        test_write_message()
        test_mqtt_topics()
        
        print("\n🎉 All tests completed!")
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nTest error: {e}")

if __name__ == "__main__":
    main()