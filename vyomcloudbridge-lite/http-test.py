import datetime
from PIL import Image
import requests
import time
import base64


def image_to_bytes(image_path):
    """
    Converts an image to bytes.
    """
    with Image.open(image_path) as img:
        return img.tobytes()


def image_to_compressed_bytes(image_path, format="JPEG"):
    """
    Converts an image to bytes in a compressed format (e.g., PNG, JPEG).
    """
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
        # 1. Encode the raw bytes into Base64
        base64_bytes = base64.b64encode(image_bytes)

        # 2. Decode the Base64 bytes into a clean string for JSON
        base64_string = base64_bytes.decode("utf-8")
    return base64_string


def call_n8n_workflow(image_bytes):
    """
    Calls the n8n workflow to process the image.
    """
    # API call here
    url = "https://n8n.vyomos.org/webhook-test/watchmen-detect/"

    date = datetime.datetime.now().strftime("%Y-%m-%d")
    machine_id = 228

    # Set headers for binary data
    payload = {
        "date": date,
        "s3_bucket": "vyomos",
        "organization_id": 20,
        "message_type": "event",
        "machine_id": machine_id,
        "file_path": f"20/_all_/{date}/{machine_id}/_all_/images",
        "topic": f"20/_all_/{date}/{machine_id}/_all_/events/{int(time.time())}.json",
        "timestamp": int(time.time()),
        "image": image_bytes,
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

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None


if __name__ == "__main__":
    image_path = "/Users/caleb/Downloads/gun-men.jpg"
    image_bytes = image_to_compressed_bytes(image_path)
    try:
        response = call_n8n_workflow(image_bytes)
        print(response)
    except Exception as e:
        print(f"Error calling n8n workflow: {e}")
