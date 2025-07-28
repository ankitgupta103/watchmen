#!/usr/bin/env python3
"""
MicroPython Compatibility Test Suite
Tests the vyomcloudbridge-lite package for MicroPython v1.25 compatibility
"""

import sys
import os
import json
import time
import gc

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test filesystem queue
        from filesystem_queue import FilesystemQueue
        print("✓ filesystem_queue imported successfully")
        
        # Test MQTT client (will show warning about umqtt but should not crash)
        try:
            from mqtt_client import VyomMqttClient
            print("✓ mqtt_client imported successfully")
        except ImportError as e:
            if "umqtt" in str(e):
                print("⚠ mqtt_client import warning: umqtt not available (expected in regular Python)")
            else:
                raise
        
        # Test message handler
        try:
            from message_handler import MessageSender, MessageListener, VyomCloudBridgeLite
            print("✓ message_handler imported successfully")
        except ImportError as e:
            if "umqtt" in str(e):
                print("⚠ message_handler import warning: umqtt dependency (expected in regular Python)")
            else:
                raise
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_filesystem_queue():
    """Test filesystem queue functionality"""
    print("\nTesting filesystem queue...")
    
    try:
        from filesystem_queue import FilesystemQueue
        
        # Create test directory
        test_dir = "/tmp/test_queue_micropython"
        
        # Initialize queue
        queue = FilesystemQueue(test_dir, max_size=3)
        
        # Test enqueue
        test_messages = [
            {"type": "test", "id": 1, "data": "message 1"},
            {"type": "test", "id": 2, "data": "message 2"},
            {"type": "test", "id": 3, "data": "message 3"}
        ]
        
        for msg in test_messages:
            success = queue.enqueue(msg, f"topic_{msg['id']}")
            assert success, f"Failed to enqueue message {msg['id']}"
        
        print(f"✓ Enqueued {len(test_messages)} messages")
        
        # Test size
        size = queue.size()
        assert size == 3, f"Expected size 3, got {size}"
        print(f"✓ Queue size correct: {size}")
        
        # Test peek
        peeked = queue.peek()
        assert peeked is not None, "Peek returned None"
        assert peeked["message"]["id"] == 1, "Peek returned wrong message"
        print("✓ Peek functionality works")
        
        # Test dequeue
        dequeued_messages = []
        while queue.size() > 0:
            item = queue.dequeue()
            assert item is not None, "Dequeue returned None"
            dequeued_messages.append(item)
        
        assert len(dequeued_messages) == 3, "Wrong number of dequeued messages"
        print("✓ Dequeue functionality works")
        
        # Test max size enforcement
        for i in range(5):  # Try to add more than max_size
            queue.enqueue({"id": i}, "test")
        
        final_size = queue.size()
        assert final_size <= 3, f"Queue exceeded max size: {final_size}"
        print("✓ Max size enforcement works")
        
        # Cleanup
        queue.clear()
        assert queue.size() == 0, "Queue not properly cleared"
        print("✓ Queue cleanup works")
        
        return True
        
    except Exception as e:
        print(f"✗ Filesystem queue test failed: {e}")
        return False

def test_json_compatibility():
    """Test JSON serialization/deserialization"""
    print("\nTesting JSON compatibility...")
    
    try:
        # Test complex data structure
        test_data = {
            "timestamp": int(time.time() * 1000),
            "device_id": "test-device-001",
            "sensors": {
                "temperature": 25.5,
                "humidity": 60.2,
                "pressure": 1013.25
            },
            "status": True,
            "tags": ["sensor", "environment", "monitoring"],
            "metadata": {
                "version": "1.0",
                "location": {"lat": 40.7128, "lon": -74.0060}
            }
        }
        
        # Serialize
        json_str = json.dumps(test_data)
        assert len(json_str) > 0, "JSON serialization failed"
        print("✓ JSON serialization works")
        
        # Deserialize
        parsed_data = json.loads(json_str)
        assert parsed_data["device_id"] == test_data["device_id"], "JSON deserialization failed"
        assert parsed_data["sensors"]["temperature"] == test_data["sensors"]["temperature"], "Nested data lost"
        print("✓ JSON deserialization works")
        
        return True
        
    except Exception as e:
        print(f"✗ JSON compatibility test failed: {e}")
        return False

def test_memory_management():
    """Test memory management with garbage collection"""
    print("\nTesting memory management...")
    
    try:
        # Get initial memory state
        gc.collect()
        
        # Create and destroy many objects
        for i in range(100):
            data = {
                "id": i,
                "data": "x" * 100,  # Some data
                "nested": {"value": i * 2}
            }
            
            # Convert to JSON and back
            json_str = json.dumps(data)
            parsed = json.loads(json_str)
            
            # Explicit cleanup
            del data, json_str, parsed
            
            # Periodic garbage collection
            if i % 10 == 0:
                gc.collect()
        
        # Final cleanup
        gc.collect()
        print("✓ Memory management test completed without crashes")
        
        return True
        
    except Exception as e:
        print(f"✗ Memory management test failed: {e}")
        return False

def test_file_operations():
    """Test file I/O operations"""
    print("\nTesting file operations...")
    
    try:
        test_file = "/tmp/micropython_test.json"
        
        # Test write
        test_data = {
            "test": "file_operations",
            "timestamp": int(time.time()),
            "data": ["item1", "item2", "item3"]
        }
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        print("✓ File write operation works")
        
        # Test read
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["test"] == test_data["test"], "File read/write mismatch"
        print("✓ File read operation works")
        
        # Test file existence check
        assert os.path.exists(test_file), "File existence check failed"
        print("✓ File existence check works")
        
        # Test directory operations
        test_dir = "/tmp/micropython_test_dir"
        try:
            os.makedirs(test_dir)
        except OSError:
            pass  # Directory might already exist
        
        assert os.path.exists(test_dir), "Directory creation failed"
        print("✓ Directory operations work")
        
        # Cleanup
        try:
            os.remove(test_file)
            os.rmdir(test_dir)
        except OSError:
            pass
        
        return True
        
    except Exception as e:
        print(f"✗ File operations test failed: {e}")
        return False

def test_time_functions():
    """Test time-related functions"""
    print("\nTesting time functions...")
    
    try:
        # Test basic time functions
        current_time = time.time()
        assert current_time > 0, "time.time() returned invalid value"
        print("✓ time.time() works")
        
        # Test millisecond timestamp
        timestamp_ms = int(time.time() * 1000)
        expected_min = int(current_time * 1000)
        assert timestamp_ms >= expected_min, f"Millisecond timestamp calculation failed: {timestamp_ms} < {expected_min}"
        print("✓ Millisecond timestamp calculation works")
        
        # Test sleep function
        start_time = time.time()
        time.sleep(0.1)
        end_time = time.time()
        sleep_duration = end_time - start_time
        
        assert 0.08 <= sleep_duration <= 0.2, f"Sleep duration unexpected: {sleep_duration}"
        print("✓ time.sleep() works")
        
        return True
        
    except Exception as e:
        print(f"✗ Time functions test failed: {e}")
        return False

def test_string_operations():
    """Test string operations used in the package"""
    print("\nTesting string operations...")
    
    try:
        # Test topic parsing (common operation)
        topic = "vyom-mqtt-msg/device-001/sensor/temperature/1640995200000.json"
        parts = topic.split("/")
        
        assert len(parts) == 5, f"Topic split failed: {parts}"
        assert parts[1] == "device-001", "Topic parsing failed"
        print("✓ String splitting works")
        
        # Test string formatting
        machine_id = "test-device"
        data_source = "sensors"
        timestamp = 1640995200000
        
        formatted_topic = f"vyom-mqtt-msg/{machine_id}/{data_source}/{timestamp}"
        expected = "vyom-mqtt-msg/test-device/sensors/1640995200000"
        
        assert formatted_topic == expected, f"String formatting failed: {formatted_topic}"
        print("✓ String formatting works")
        
        # Test string operations
        test_str = "  Hello MicroPython  "
        stripped = test_str.strip()
        lower_case = stripped.lower()
        
        assert stripped == "Hello MicroPython", "String strip failed"
        assert lower_case == "hello micropython", "String lowercase failed"
        print("✓ String operations work")
        
        return True
        
    except Exception as e:
        print(f"✗ String operations test failed: {e}")
        return False

def test_error_handling():
    """Test error handling mechanisms"""
    print("\nTesting error handling...")
    
    try:
        # Test try/except with file operations
        try:
            with open("/nonexistent/file.json", 'r') as f:
                f.read()
            assert False, "Should have raised an exception"
        except (OSError, IOError):
            print("✓ File error handling works")
        
        # Test try/except with JSON parsing
        try:
            json.loads("invalid json {")
            assert False, "Should have raised an exception"
        except json.JSONDecodeError:
            print("✓ JSON error handling works")
        except ValueError:  # MicroPython might raise ValueError instead
            print("✓ JSON error handling works (ValueError)")
        
        # Test finally blocks
        test_var = False
        try:
            raise Exception("Test exception")
        except Exception:
            pass
        finally:
            test_var = True
        
        assert test_var, "Finally block didn't execute"
        print("✓ Finally blocks work")
        
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

def run_all_tests():
    """Run all compatibility tests"""
    print("MicroPython v1.25 Compatibility Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Filesystem Queue", test_filesystem_queue),
        ("JSON Compatibility", test_json_compatibility),
        ("Memory Management", test_memory_management),
        ("File Operations", test_file_operations),
        ("Time Functions", test_time_functions),
        ("String Operations", test_string_operations),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<20} {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Package is MicroPython v1.25 compatible!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review compatibility issues.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)