import time
import socket
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from test_device import Device
from test_central import CommandCentral 
from test_camera import USBCamera

def get_hostname():
    """Get system hostname"""
    return socket.gethostname()

def get_device_id():
    """Determine device ID based on hostname or configuration"""
    hn = get_hostname()
    
    # Map hostnames to device IDs
    hostname_map = {
        "central": "CC",
        "rpi2": "CAM_002", 
        "rpi3": "CAM_003",
        "rpi4": "CAM_004",
        "rpi5": "CAM_005"
    }
    
    return hostname_map.get(hn, f"CAM_{hn.upper()}")

def check_root_permissions():
    """Check if running with required permissions"""
    if os.geteuid() != 0:
        print("ERROR: This system requires root permissions for GPIO access")
        print("Please run with: sudo python3 run_usb_camera_demo.py")
        return False
    return True

def setup_directories():
    """Create required directories"""
    directories = [
        "/tmp/camera_captures",
        "/tmp/camera_archive", 
        "/var/log"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Directory ready: {directory}")

def test_usb_camera_standalone():
    """Test USB camera system standalone"""
    print("=== Testing USB Camera System (Standalone) ===")
    
    if not check_root_permissions():
        return False
        
    setup_directories()
    
    try:
        # Create standalone USB camera
        camera = USBCamera("STANDALONE_TEST", "standalone_test")
        
        print("USB Camera initialized successfully")
        print("Starting image capture cycle...")
        
        # Run a few test cycles
        for cycle in range(3):
            print(f"\n--- Test Cycle {cycle + 1} ---")
            filepath, result = camera.take_picture()
            print(f"Cycle result: {result}")
            
            # Wait between cycles
            if cycle < 2:  # Don't wait after last cycle
                print("Waiting 30 seconds before next cycle...")
                time.sleep(30)
        
        # Print final statistics
        print(f"\n=== Final Statistics ===")
        print(f"Images processed: {camera.image_count}")
        print(f"Detections made: {camera.detection_count}")
        print(f"Health events: {len(camera.health_events)}")
        print(f"Suspicious events: {len(camera.suspicious_events)}")
        
        return True
        
    except Exception as e:
        print(f"Standalone test failed: {e}")
        return False
    finally:
        try:
            camera.cleanup()
        except:
            pass

def run_camera_device():
    """Run as a camera-enabled device in standalone mode"""
    print("=== Running as Camera Device (Standalone Mode) ===")
    
    if not check_root_permissions():
        return False
        
    setup_directories()
    
    devid = get_device_id()
    mission_id = "usb_camera_surveillance"
    
    print(f"Device ID: {devid}")
    print(f"Mission ID: {mission_id}")
    print("Communication: DISABLED (running standalone)")
    
    try:
        # Create device with camera capabilities - no communication
        device = Device(devid, mission_id=mission_id)
        
        print(f"Camera device {devid} initialized successfully")
        
        # Run operational cycle
        cycle_count = 0
        while True:
            cycle_count += 1
            print(f"\n=== Operational Cycle {cycle_count} ===")
            
            try:
                # Network discovery (disabled but logged)
                print("Network scan (disabled - standalone mode)")
                device.send_scan(time.time_ns())
                
                # Check for events (triggers USB camera) - main functionality
                print("Checking for surveillance events...")
                device.check_event()
                
                # Send heartbeat (disabled but logged)  
                print("Heartbeat (disabled - standalone mode)")
                device.send_hb(time.time_ns())
                
                # Print device status
                status = device.get_status_summary()
                print(f"Device Status: {json.dumps(status, indent=2)}")
                
                # Print camera events if available
                if device.camera:
                    events = device.camera.get_events_for_central()
                    if events["health_events"] or events["suspicious_events"]:
                        print("Camera Events:")
                        print(json.dumps(events, indent=2))
                
                # Wait before next cycle
                cycle_wait = 120  # 2 minutes between cycles
                print(f"Waiting {cycle_wait} seconds before next cycle...")
                time.sleep(cycle_wait)
                
            except KeyboardInterrupt:
                print("\nOperation stopped by user")
                break
            except Exception as e:
                print(f"Cycle {cycle_count} failed: {e}")
                time.sleep(30)  # Wait before retrying
                
    except Exception as e:
        print(f"Camera device initialization failed: {e}")
        return False
    finally:
        try:
            device.cleanup()
        except:
            pass

def run_command_central():
    """Run as command central with MQTT publishing"""
    print("=== Running as Command Central (MQTT Publishing Enabled) ===")
    
    mission_id = "watchmen_surveillance"
    
    try:
        cc = CommandCentral("CC", mission_id=mission_id)
        
        print("Command Central initialized successfully")
        print("Communication: DISABLED (standalone mode)")
        print("MQTT Publishing: ENABLED")
        
        # Run command central operations
        for cycle in range(10):
            print(f"\n=== Command Central Cycle {cycle + 1} ===")
            
            time.sleep(10)
            
            # Send shortest path updates (disabled)
            print("Sending shortest path updates (disabled)")
            cc.send_spath()
            
            time.sleep(10)
            
            # Display network status and publish events
            print("Collecting events and publishing to MQTT...")
            cc.console_output()
            
            print(f"Cycle {cycle + 1} completed")
            
        print("Command Central operations completed")
        
    except Exception as e:
        print(f"Command Central failed: {e}")
        return False

def run_integrated_system():
    """Run integrated system with multiple camera devices and central command"""
    print("=== Running Integrated System (Multiple Devices + Central) ===")
    
    if not check_root_permissions():
        return False
        
    setup_directories()
    
    mission_id = "integrated_surveillance"
    
    try:
        cc = CommandCentral("CC", mission_id=mission_id)
        
        camera_devices = []
        device_ids = ["CAM_001", "CAM_002", "CAM_003"]
        
        for dev_id in device_ids:
            try:
                device = Device(dev_id, mission_id=mission_id)
                camera_devices.append(device)
                print(f"Created camera device: {dev_id}")
            except Exception as e:
                print(f"Failed to create device {dev_id}: {e}")
        
        if not camera_devices:
            print("No camera devices created successfully")
            return False
        
        print(f"Created {len(camera_devices)} camera devices")
        print("Starting integrated monitoring...")
        
        # Run integrated monitoring
        cc.run_standalone_monitoring(camera_devices, monitoring_interval=180)  # 3 minutes between cycles
        
    except KeyboardInterrupt:
        print("\nIntegrated system stopped by user")
    except Exception as e:
        print(f"Integrated system failed: {e}")
        return False
    finally:
        try:
            cc.cleanup()
            for device in camera_devices:
                device.cleanup()
        except:
            pass

def run_continuous_monitoring():
    """Run continuous monitoring mode"""
    print("=== Running Continuous Monitoring Mode ===")
    
    if not check_root_permissions():
        return False
        
    setup_directories()
    
    devid = get_device_id()
    mission_id = "continuous_surveillance"
    
    try:
        # Create USB camera for continuous monitoring
        camera = USBCamera(devid, mission_id)
        
        print(f"Starting continuous monitoring for device {devid}")
        print("Press Ctrl+C to stop monitoring")
        
        # Run continuous cycle with 5-minute intervals
        camera.run_continuous_cycle(cycle_interval=300)
        
    except KeyboardInterrupt:
        print("\nContinuous monitoring stopped by user")
    except Exception as e:
        print(f"Continuous monitoring failed: {e}")
        return False

def print_usage():
    """Print usage information"""
    print("USB Camera System Demo")
    print("Usage: sudo python3 run_usb_camera_demo.py [mode]")
    print()
    print("Modes:")
    print("  test          - Test USB camera standalone")
    print("  device        - Run as camera device (standalone)")
    print("  central       - Run as command central (MQTT publishing)")
    print("  integrated    - Run integrated system (multiple devices + central)")
    print("  continuous    - Run continuous monitoring")
    print("  help          - Show this help")
    print()
    print("Note: Device-to-device communication is DISABLED")
    print("      Only central device publishes to MQTT")
    print()
    print("Examples:")
    print("  sudo python3 run_usb_camera_demo.py test")
    print("  sudo python3 run_usb_camera_demo.py device")
    print("  sudo python3 run_usb_camera_demo.py integrated")

def main():
    """Main entry point"""
    # Check command line arguments
    if len(sys.argv) < 2:
        print_usage()
        return 1
        
    mode = sys.argv[1].lower()
    
    print(f"Starting USB Camera System Demo in '{mode}' mode")
    print(f"Timestamp: {datetime.now()}")
    print(f"Hostname: {get_hostname()}")
    print(f"Device ID: {get_device_id()}")
    print("Communication: DISABLED (standalone operation)")
    print("MQTT: Only from central device")
    print("=" * 50)
    
    try:
        if mode == "test":
            success = test_usb_camera_standalone()
            
        elif mode == "device":
            success = run_camera_device()
            
        elif mode == "central":
            success = run_command_central()
            
        elif mode == "integrated":
            success = run_integrated_system()
            
        elif mode == "continuous":
            success = run_continuous_monitoring()
            
        elif mode == "help":
            print_usage()
            return 0
            
        else:
            print(f"Unknown mode: {mode}")
            print_usage()
            return 1
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nDemo stopped by user")
        return 0
    except Exception as e:
        print(f"Demo failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())