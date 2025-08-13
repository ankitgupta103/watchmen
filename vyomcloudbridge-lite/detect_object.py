import os
import io
import base64
import argparse
import json
import logging
from typing import List, Dict, Any, Optional

import requests
from ultralytics import YOLO
from PIL import Image

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Config:
    MODEL_PATH = "yolov8l.pt"
    CONFIDENCE_THRESHOLD = 0.3

    RELEVANT_CLASSES = {
        0: "person",
        24: "backpack",
        26: "handbag",
        28: "suitcase",
        43: "knife",
    }


class ObjectDetector:
    def __init__(self, model_path: str):
        """
        Initializes the ObjectDetector.

        Args:
            model_path (str): The path to the YOLO model file.
        """
        self.model: Optional[YOLO] = None
        self._load_model(model_path)

    def _load_model(self, model_path: str) -> None:
        try:
            logging.info(f"Loading YOLO model from {model_path}...")
            if not os.path.exists(model_path):
                logging.warning(
                    f"Model file not found at {model_path}. YOLO will attempt to download it."
                )
            self.model = YOLO(model_path)
            logging.info("Model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load model: {e}")
            raise

    def detect(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Performs object detection on a given image.

        Args:
            image (Image.Image): The input image in PIL format.

        Returns:
            List[Dict[str, Any]]: A list of detected objects with their details.
        """
        if not self.model:
            raise RuntimeError("Model is not loaded.")

        try:
            results = self.model(image)
            detections = []

            for result in results:
                if not result.boxes:
                    continue

                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])

                    if (
                        class_id in Config.RELEVANT_CLASSES
                        and confidence >= Config.CONFIDENCE_THRESHOLD
                    ):

                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        detections.append(
                            {
                                "class_name": Config.RELEVANT_CLASSES[class_id],
                                "confidence": round(confidence, 4),
                                "bounding_box": {
                                    "x": x1,
                                    "y": y1,
                                    "width": x2 - x1,
                                    "height": y2 - y1,
                                },
                            }
                        )

            return detections
        except Exception as e:
            logging.error(f"An error occurred during detection: {e}")
            raise


def get_image_from_source(
    url: Optional[str] = None, b64_string: Optional[str] = None
) -> Image.Image:
    """
    Loads an image from a URL or a base64 encoded string.

    Args:
        url (Optional[str]): The URL of the image.
        b64_string (Optional[str]): The base64 encoded image string.

    Returns:
        Image.Image: The loaded image as a PIL object.

    Raises:
        ValueError: If the input is invalid or the image cannot be opened.
    """
    image_bytes = None
    if url:
        try:
            logging.info(f"Fetching image from URL: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            image_bytes = response.content
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch image from URL: {e}")
    elif b64_string:
        try:
            logging.info("Decoding base64 image string...")
            image_bytes = base64.b64decode(b64_string)
        except (base64.binascii.Error, ValueError) as e:
            raise ValueError(f"Invalid base64 string: {e}")

    if not image_bytes:
        raise ValueError("No valid image source provided.")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Convert image to RGB if it has an alpha channel (e.g., PNG)
        if image.mode != "RGB":
            image = image.convert("RGB")
        logging.info("Image loaded and prepared successfully.")
        return image
    except Exception as e:
        raise ValueError(f"Failed to open or process image data: {e}")


def main():
    """Main function to run the object detection script."""
    parser = argparse.ArgumentParser(
        description="Detect persons and bags in an image using YOLOv8."
    )

    # Create a mutually exclusive group to ensure only one input type is provided
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", type=str, help="URL of the image to process.")
    input_group.add_argument(
        "--base64", type=str, help="Base64 encoded string of the image."
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save the JSON output to a file.",
    )

    args = parser.parse_args()

    try:
        # Step 1: Initialize the detector
        detector = ObjectDetector(model_path=Config.MODEL_PATH)

        # Step 2: Load the image from the specified source
        image = get_image_from_source(url=args.url, b64_string=args.base64)

        # Step 3: Run detection
        detections = detector.detect(image)

        # Step 4: Prepare the final output
        output_data = {"detections": detections, "count": len(detections)}

        # Pretty-print the JSON output
        json_output = json.dumps(output_data, indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(json_output)
            logging.info(f"✅ Detection complete. Results saved to {args.output}")
        else:
            print(json_output)
            logging.info(f"✅ Detection complete. Found {len(detections)} objects.")

    except (ValueError, RuntimeError, Exception) as e:
        logging.error(f"An error occurred: {e}")
        # Exit with a non-zero status code to indicate failure
        exit(1)


if __name__ == "__main__":
    main()
