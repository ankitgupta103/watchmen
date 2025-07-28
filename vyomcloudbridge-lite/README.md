# VyomCloudBridge Lite - Watchmen Device Registration

A minimal version of vyomcloudbridge designed specifically for MicroPython devices that only handles device registration with VyomIQ.

## Features

- Device registration with VyomIQ API
- Configuration file management
- IoT credentials storage (if provided by API)
- Minimal dependencies for MicroPython compatibility

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Interactive Mode (Default)
```bash
python setup.py
```

### Non-Interactive Mode
```bash
python setup.py --non-interactive
```

In non-interactive mode, the script will use environment variables:
- `DEVICE_UID`: Device unique identifier (defaults to 'watchmen-device')
- `DEVICE_NAME`: Device name (defaults to 'Watchmen Device')

## Configuration

The device configuration is stored in `/opt/vyomcloudbridge/machine_config.ini` and includes:

### Machine Section
- `machine_id`: Unique machine ID from VyomIQ
- `machine_uid`: Device UID provided during registration
- `machine_name`: Device name provided during registration
- `machine_model_id`: Machine model ID from VyomIQ
- `machine_model_name`: Machine model name
- `machine_model_type`: Machine model type
- `organization_id`: Organization ID
- `organization_name`: Organization name
- `created_at`: Registration timestamp
- `updated_at`: Last update timestamp
- `session_id`: Session ID for API communication

### IoT Section (if provided)
- `thing_name`: AWS IoT thing name
- `thing_arn`: AWS IoT thing ARN
- `policy_name`: AWS IoT policy name
- `certificate`: AWS IoT certificate
- `private_key`: AWS IoT private key
- `public_key`: AWS IoT public key
- `root_ca`: AWS IoT root CA certificate

## API Endpoint

The device registration uses the endpoint: `https://api.vyomiq.com/device/register/watchmen`

## Organization

This setup is configured for Watchmen devices with organization ID: 20

## Error Handling

The script includes comprehensive error handling for:
- Network timeouts
- API errors
- Configuration file issues
- Missing dependencies

## MicroPython Compatibility

This minimal version is designed to be compatible with MicroPython environments by:
- Using only standard library modules where possible
- Minimizing external dependencies
- Avoiding system-specific operations
- Keeping the codebase lightweight 