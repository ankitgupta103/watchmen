# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Post files with HTTP/Post requests module example - Modified for 4G connectivity

import time
import json

# Import the SIM7600X class (save the previous code as sim7600x.py)
from sim7600x import SIM7600X

# API Configuration
URL = "https://n8n.vyomos.org/webhook/watchmen-detect"
# URL = "https://n8n.vyomos.org/webhook/test/watchmen-detect"

# Initialize 4G modem instead of WiFi
print("Initializing 4G connection...")
sim = SIM7600X(uart_id=1, baudrate=115200)

# Connect to 4G network (change APN for your carrier)
if not sim.init_module(apn="airtelgprs.com"):  # Use your carrier's APN
    print("4G connection failed!")
    exit()

print("4G Connected successfully!")

# Define the payload (same as original)
machine_id = 228  # Hardcoded for now, extract from machine.id
organization_id = 20  # Hardcoded for now, extract from organization.id
date = "2025-08-05"  # YYYY-MM-DD format 
s3_bucket = "vyomos"  # Always the same
message_type = "test"  # Can be event or test
topic = f"20/_all_/{date}/{machine_id}/_all_/events/{int(time.time())}.json"
file_path = f"20/_all_/{date}/{machine_id}/_all_/images"
example_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"

# Create payload (same as original)
payload = {
    "machine_id": machine_id,
    "organization_id": organization_id,
    "date": date,
    "s3_bucket": s3_bucket,
    "message_type": message_type,
    "file_path": file_path,
    "image": example_image,
    "topic": topic,
    "timestamp": int(time.time()),
    "email_list": [
        "caleb@vyomos.org",
        "anand@vyomos.org",
        "vaseka@vyomos.org",
        "amardeep@vyomos.org",
    ],
    "phone_list": [
        "+917597050815",
        "+919044268425",
    ],
}

# Convert to JSON
json_payload = json.dumps(payload)

# Debug: Print the exact payload being sent
print("=== PAYLOAD DEBUG ===")
print("Full JSON payload:")
print(json_payload)
print(f"Payload length: {len(json_payload)} bytes")
print("=====================")

print("Sending data to server...")

# Send via 4G instead of requests.post()
success, response = sim.http_post(URL, json_payload)

if success:
    print(" Data sent successfully!")
    print("=== SERVER RESPONSE ===")
    print(response)
    print("=======================")
    
    # Check if response contains success indicators
    if "Workflow was started" in response:
        print(" n8n workflow was triggered!")
    elif "200" in response:
        print(" HTTP 200 received - check n8n logs")
    else:
        print(" Unexpected response - check n8n webhook config")
else:
    print(" Failed to send data")
    print("Response:", response)

print("Done!")