# VyomCloudBridge Lite

A simplified, MicroPython v1.25 compatible version of VyomCloudBridge focusing on the core `write_message` functionality for MQTT messaging.

## 🎯 Overview

VyomCloudBridge Lite is a streamlined version of the original VyomCloudBridge package, designed specifically for MicroPython environments. It provides the essential `write_message` functionality with the same MQTT topic paths as the original, while removing complex dependencies like AWS IoT SDK, RabbitMQ, ROS, and MAVLink.

## ✨ Key Features

- **MicroPython v1.25 Compatible**: Tested and verified for MicroPython compatibility
- **Simplified MQTT Client**: Uses `umqtt.simple` or `umqtt.robust` libraries
- **Same Topic Paths**: Uses identical MQTT topic format as original vyomcloudbridge
- **Filesystem Queue**: Replaces RabbitMQ with simple file-based message queuing
- **Event Handlers**: Includes `on_event_arrive`, `on_hb_arrive`, and `on_image_arrive` handlers
- **Memory Efficient**: Designed for resource-constrained environments
- **Offline Support**: Queues messages when disconnected

## 🏗️ Architecture

```
VyomClient
├── write_message()     # Main messaging function (compatible API)
├── MQTT Client        # umqtt-based client with reconnection
├── Filesystem Queue   # File-based message queuing
└── Event Handlers     # on_event_arrive, on_hb_arrive, on_image_arrive
```

## 📦 Installation

### For MicroPython:
```bash
# Install umqtt library
upip install micropython-umqtt.simple
# or
upip install micropython-umqtt.robust
```

### For regular Python (testing):
```bash
pip install micropython-umqtt.simple micropython-umqtt.robust
```

## 🚀 Quick Start

```python
from vyom_client import VyomClient

# Create configuration
config = {
    "server": "mqtt.broker.com",
    "port": 1883,
    "machine_id": "device-001",
    "organization_id": "20",
    "user": "username",
    "password": "password"
}

# Initialize client
client = VyomClient(config)

# Send telemetry data
telemetry = {
    "temperature": 25.5,
    "humidity": 60.2,
    "battery": 85
}

success, error = client.write_message(
    message_data=telemetry,
    data_type="json",
    data_source="sensors",
    destination_ids=["s3", "hq"]
)

if success:
    print("Message sent successfully!")
else:
    print(f"Failed to send: {error}")

# Cleanup
client.cleanup()
```

## 📋 API Reference

### VyomClient

#### Constructor
```python
VyomClient(config)
```

**Parameters:**
- `config`: Dictionary with MQTT broker configuration

#### write_message()
```python
write_message(message_data, data_type, data_source, destination_ids, 
              filename=None, mission_id=None, project_id=None, 
              priority=1, send_live=False, background=False)
```

**Parameters:**
- `message_data`: The data to send (dict, str, bytes)
- `data_type`: Type of data ("json", "image", "binary")
- `data_source`: Source identifier ("telemetry", "camera1", "sensors", etc.)
- `destination_ids`: List of destination IDs (["s3", "hq", "gcs_mqtt"])
- `filename`: Optional custom filename
- `mission_id`: Mission ID (compatibility, not used)
- `project_id`: Project ID (compatibility, not used)
- `priority`: Message priority (compatibility, not used)
- `send_live`: Send as live data (compatibility, not used)
- `background`: Send in background (compatibility, not used)

**Returns:**
- `tuple`: (success: bool, error_message: str or None)

#### Utility Methods
```python
# Send heartbeat
client.send_heartbeat(status="online", extra_data=None)

# Send telemetry
client.send_telemetry(telemetry_data, destination_ids=None)

# Send image
client.send_image(image_data, camera_id="camera1", destination_ids=None)

# Get status
status = client.get_status()
```

#### Event Handlers
```python
# Set event handlers
def handle_event(event_data):
    print(f"Event: {event_data}")

def handle_heartbeat(hb_data):
    print(f"Heartbeat: {hb_data}")

def handle_image(img_data):
    print(f"Image: {len(img_data)} bytes")

client.on_event_arrive = handle_event
client.on_hb_arrive = handle_heartbeat
client.on_image_arrive = handle_image
```

## 🎯 MQTT Topic Format

Messages are published using the same topic format as the original vyomcloudbridge:

```
vyom-mqtt-msg/{destination_id}/{machine_id}/{data_source}/{filename}
```

**Examples:**
- `vyom-mqtt-msg/s3/device-001/sensors/1640995200000.json`
- `vyom-mqtt-msg/hq/device-001/camera1/1640995201000.jpg`
- `vyom-mqtt-msg/gcs_mqtt/device-001/telemetry/1640995202000.json`

## 📁 File Structure

```
vyomcloudbridge-lite/
├── vyom_client.py           # Main VyomClient class
├── filesystem_queue.py      # File-based message queue
├── mqtt_client.py           # MQTT client wrapper
├── mock_umqtt.py           # Mock MQTT for testing
├── test_vyom_client.py     # Test suite
├── test_micropython.py     # MicroPython compatibility tests
├── requirements.txt        # Dependencies
├── config.json            # Default configuration
└── README_LITE.md         # This file
```

## 🧪 Testing

Run the test suite:
```bash
# Test VyomClient functionality
python3 test_vyom_client.py

# Test MicroPython compatibility
python3 test_micropython.py
```

## 🔧 Configuration

Create a configuration dictionary:
```python
config = {
    "server": "mqtt.broker.com",     # MQTT broker hostname
    "port": 1883,                    # MQTT broker port
    "machine_id": "device-001",      # Unique device identifier
    "organization_id": "20",         # Organization ID
    "user": "username",              # MQTT username (optional)
    "password": "password",          # MQTT password (optional)
    "keepalive": 60                  # MQTT keepalive seconds
}
```

## 📝 Examples

### Basic Telemetry
```python
from vyom_client import VyomClient, create_default_config

client = VyomClient(create_default_config())

# Send sensor data
sensor_data = {
    "timestamp": int(time.time() * 1000),
    "temperature": 23.5,
    "humidity": 65.2,
    "pressure": 1013.25
}

success, error = client.write_message(
    message_data=sensor_data,
    data_type="json",
    data_source="weather_station",
    destination_ids=["s3", "hq"]
)
```

### Image Data
```python
# Send image data
with open("image.jpg", "rb") as f:
    image_data = f.read()

success, error = client.send_image(
    image_data, 
    camera_id="camera1", 
    destination_ids=["s3"]
)
```

### Custom Event
```python
# Send custom event
event_data = {
    "event_type": "alarm",
    "severity": "high",
    "message": "Temperature threshold exceeded",
    "sensor_id": "temp_01"
}

success, error = client.write_message(
    message_data=event_data,
    data_type="json",
    data_source="alerts",
    destination_ids=["hq", "gcs_mqtt"]
)
```

## 🔄 Differences from Original

| Feature | Original VyomCloudBridge | VyomCloudBridge Lite |
|---------|-------------------------|---------------------|
| Dependencies | AWS IoT SDK, RabbitMQ, ROS | umqtt only |
| Message Queue | RabbitMQ | Filesystem-based |
| MQTT Client | AWS IoT Core client | umqtt client |
| Listeners | Full listener system | Event handlers only |
| Services | Multiple background services | None |
| Platform | Full Python | MicroPython v1.25 |
| Memory Usage | High | Optimized |

## 🐛 Troubleshooting

### Common Issues

1. **umqtt not found**: Install `micropython-umqtt.simple` or `micropython-umqtt.robust`
2. **Connection failed**: Check MQTT broker settings and network connectivity
3. **Queue directory errors**: Ensure filesystem has write permissions
4. **Memory issues**: Call `gc.collect()` periodically in tight loops

### Debug Mode
```python
# Enable verbose output
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📄 License

Same license as the original VyomCloudBridge project.

## 🤝 Contributing

1. Test changes with `test_micropython.py`
2. Ensure MicroPython v1.25 compatibility
3. Keep memory usage minimal
4. Maintain API compatibility with original `write_message`

---

**Note**: This is a simplified version designed for MicroPython environments. For full features, use the original VyomCloudBridge package.