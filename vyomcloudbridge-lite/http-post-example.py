# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Post files with HTTP/Post requests module example

import network
import requests
import time
import json

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

# Define the headers to specify content type
headers = {"Content-Type": "application/json"}

# Define the payload (TODO: Make it dynamic {Anand})
machine_id = 228  # Hardcoded for now, extract from machine.id
message_type = "event"  # Can be event or test (Hardcoded for now)
example_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"

# Send some files
payload = {
    "machine_id": machine_id,
    "message_type": message_type,
    "image": example_image,
}

# Manually convert the dictionary to a JSON string
json_payload = json.dumps(payload)

# Send the request using data= and headers= parameters
r = requests.post(URL, data=json_payload, headers=headers)

# Print the response from the server
print("Status:", r.status_code)
print("Headers:", r.headers)
print("Content:", r.content)
