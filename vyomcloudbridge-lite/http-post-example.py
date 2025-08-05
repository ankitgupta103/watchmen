# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Post files with HTTP/Post requests module example

import network
import requests
import time
import json  # <-- 1. IMPORT THE JSON LIBRARY

# AP info
SSID = "BWH07-STARTUP1"  # Network SSID
KEY = "Hf3BjATM"  # Network key
URL = "https://n8n.vyomos.org/webhook/watchmen-detect"

# Init wlan module and connect to network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, KEY)

while not wlan.isconnected():
    print('Trying to connect to "{:s}"...'.format(SSID))
    time.sleep_ms(1000)

# We should have a valid IP now via DHCP
print("WiFi Connected ", wlan.ifconfig())

# 2. DEFINE THE HEADERS TO SPECIFY CONTENT TYPE
headers = {"Content-Type": "application/json"}

# 3. DEFINE THE PAYLOAD (TODO: Make it dynamic {Anand})
machine_id = 228  # Hardcoded for now, extract from machine.id
organization_id = 20  # Hardcoded for now, extract from organization.id
date = "2025-08-05"  # YYYY-MM-DD format (Hardcoded for now, extract from datetime.now().strftime("%Y-%m-%d") handle for micropython)
s3_bucket = "vyomos"  # Always the same
message_type = "test"  # Can be event or test (Hardcoded for now)
file_path = f"20/_all_/{date}/{machine_id}/_all_/images"  # File path will be the same for all images
example_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"

# Send some files
payload = {
    "machine_id": machine_id,
    "organization_id": organization_id,
    "date": date,
    "s3_bucket": s3_bucket,
    "message_type": message_type,
    "file_path": file_path,
    "image": example_image,
    "timestamp": int(time.time()),
}

# 3. MANUALLY CONVERT THE DICTIONARY TO A JSON STRING
json_payload = json.dumps(payload)

# 4. SEND THE REQUEST USING data= and headers= PARAMETERS
r = requests.post(URL, data=json_payload, headers=headers)

# Print the response from the server
print("Status:", r.status_code)
print("Headers:", r.headers)
print("Content:", r.content)
