# import and initilize
import time
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson
writer = QueueWriterJson()

# usecase 1, for json
epoch_ms = int(time.time() * 1000)
message_data = {
    "data": f"Test message",
    "timestamp": epoch_ms,
    "lat": 75.66666,
    "long": 73.0589455,
}
filename = f"{epoch_ms}.json"

writer.write_message(
    message_data=message_data,
    filename=filename,
    data_source="watchmen-health",
    data_type="json", # image, binary, json
    mission_id="111333",
    priority=1,
    destination_ids=["s3"],
)


# usecase 2, for image data
import requests
import time
from urllib.parse import urlparse
# Sample image URLs
image_urls = [
    "https://sample-videos.com/img/Sample-jpg-image-50kb.jpg",
    "https://sample-videos.com/img/Sample-jpg-image-500kb.jpg",
]
# Number of messages to send
for i in range(5):
    epoch_ms = int(time.time() * 1000)
    filename = f"{epoch_ms}.jpg"
    image_url = image_urls[i % len(image_urls)]

    # Download the image as binary
    response = requests.get(image_url)
    if response.status_code == 200:
        binary_data = response.content
        # Send binary data
        writer.write_message(
            message_data=binary_data,
            filename=filename,
            data_source="watchmen-suspicious",
            data_type="image",
            mission_id="_all_",
            priority=1,
            destination_ids=["s3"],
            merge_chunks= False
        )
    else:
        print(f"[Error] Failed to download {image_url} (Status: {response.status_code})")
        
            
# usecase 3, any type of file, send as binary
import requests
import time
from urllib.parse import urlparse
# Sample image URLs
pdf_file_url = "https://pdfobject.com/pdf/sample.pdf"
epoch_ms = int(time.time() * 1000)
filename = f"{epoch_ms}.pdf"
# Download the pdf as binary
response = requests.get(pdf_file_url)
if response.status_code == 200:
    binary_data = response.content
    # Send binary data
    writer.write_message(
        message_data=binary_data,
        filename=filename,
        data_source="generic",
        data_type="binary", # send as binary data
        mission_id="_all_",
        priority=1,
        destination_ids=["s3"],
        merge_chunks= False
    )
else:
    print(f"[Error] Failed to download {image_url} (Status: {response.status_code})")

# cleanup
writer.cleanup() 