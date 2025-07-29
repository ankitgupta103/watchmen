# Description: Example usage of the VyomMqttClient for OpenMV.
# This script connects to Wi-Fi and AWS IoT, then publishes a message every 5 seconds.

import time
from mqtt_client import VyomMqttClient
from constants import MACHINE_CONFIG_FILE, AWS_IOT_ENDPOINT, S3_BUCKET_NAME

# --- Wi-Fi Configuration ---
# TODO: IMPORTANT: Replace with your network credentials (Anand)
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_KEY = "YOUR_WIFI_PASSWORD"


# --- Main Execution ---
def main():
    client = None
    try:
        # 1. Initialize the client with config path and AWS endpoint
        print("Initializing MQTT Client...")
        client = VyomMqttClient(
            config_path=MACHINE_CONFIG_FILE, aws_endpoint=AWS_IOT_ENDPOINT
        )

        # 2. Connect to Wi-Fi and the MQTT broker
        if client.connect(ssid=WIFI_SSID, key=WIFI_KEY):

            # 3. Publish messages in a loop
            counter = 0
            while True:
                counter += 1
                message_payload = f"Hello from OpenMV! Message number {counter}"

                # Example for publishing a log message
                message_type = "log"
                file_name = f"log_{counter}.txt"

                # Call the publish function
                published_topic = client.publish_message(
                    message=message_payload,
                    message_type=message_type,
                    filename=file_name,
                    s3_bucket=S3_BUCKET_NAME,
                )

                if published_topic:
                    print(f"Successfully published to: {published_topic}")
                else:
                    print("Failed to publish. Check connection.")

                print("-" * 20)
                time.sleep(5)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # 4. Clean up the connection and certificate files
        if client:
            client.disconnect()


if __name__ == "__main__":
    main()
