# """
# Flowchart: Person Detection on Saved Images using Classification Model
# =======================================================================

# [Start]
#    |
#    v
# [Initialize Sensor and Load Model]
#    |
#    v
# [Ensure '/processed' Folder Exists]
#    |
#    v
# [Get List of Images in '/people' Folder]
#    |
#    v
# [For Each Image in Folder:]
#    |
#    v
# [Load Image from SD Card]
#    |
#    v
# [Run Model Prediction on Image]
#    |
#    v
# [Get Highest Confidence Label]
#    |
#    v
# [Is Label == 'person' AND Confidence > 0.5?]
#    |                      |
#   Yes                    No
#    |                      |
#    v                      v
# [Draw "PERSON"          [Skip Drawing]
#  Label on Image]             |
#    |                         |
#    +-----------+-------------+
#                |
#                v
#       [Save Image to '/processed']
#                |
#                v
#            [Next Image...]
#                |
#                v
#              [Done]

# """



import sensor, image, time, os
import ml

# Dummy sensor setup (required for OpenMV runtime)
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_windowing((240, 240))
sensor.skip_frames(time=2000)


# Load person classification model
model = ml.Model("/rom/person_detect.tflite")
print(model)

# # List of clsses this model can predict
# print("Model classes:", model.classes)
# print("Labels:", model.labels)

# Ensure /processed directory exists
# if not "processed" in os.listdir("/"):
#     os.mkdir("/processed")


# List all image files in /people directory
if "people" not in os.listdir("/"):
    raise OSError("Directory /people not found. Please create it on the SD card.")

image_files = [f for f in os.listdir("/people") if f.endswith((".jpg", ".bmp", ".png"))]



for filename in image_files:
    path = "/people/" + filename
    print("Processing:", path)

    # Load image
    img = image.Image(path)

    # Run model (classification)
    result = model.predict([img])[0].flatten().tolist()
    labels = model.labels

    # Get best label and score
    scores = sorted(zip(labels, result), key=lambda x: x[1], reverse=True)
    label, confidence = scores[0]
    print("Detected:", label, "Confidence:", confidence)

    # If person detected with high confidence, draw text and save
    if label == "person" and confidence > 0.5:
        img.draw_string(10, 10, "PERSON", color=(255, 0, 0), scale=2)

    # Save to /processed folder regardless
    save_path = "/processed/" + filename
    img.save(save_path)
    print("Saved:", save_path)



print("Finished all images.")
