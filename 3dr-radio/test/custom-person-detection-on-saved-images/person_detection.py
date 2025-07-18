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



# import sensor, image, time, os
# import ml

# log_path = "log.txt"
# def log_detection(filename, confidence, x, y, w, h):
#     with open(log_path, "a") as f:
#         line = "File: {}, Confidence: {:.2f}, BBox: ({}, {}, {}, {})\n".format(
#             filename, confidence, x, y, w, h)
#         f.write(line)

# # Dummy sensor setup (required for OpenMV runtime)
# # sensor.reset()
# # sensor.set_pixformat(sensor.RGB565)
# # sensor.set_framesize(sensor.QVGA)
# # sensor.set_windowing((240, 240))
# # sensor.skip_frames(time=2000)


# # Load person classification model
# model = ml.Model("/rom/person_detect.tflite")
# print(model)

# # List of clsses this model can predict
# # print("Model classes:", model.classes)
# # print("Labels:", model.labels)

# # Ensure /processed directory exists
# if not "processed" in os.listdir():
#     os.mkdir("processed")

# # Get expected input size from model
# input_shape = model.input_shape[0]  # Should be (1, 96, 96, 1)
# _, h, w, _ = input_shape
# print("Model expects input size:", w, "x", h)


# # List all image files in /people directory
# if "people" not in os.listdir():
#     raise OSError("Directory /people not found. Please create it on the SD card.")

# image_files = [f for f in os.listdir("people") if f.endswith((".jpg", ".bmp", ".png"))]


# for filename in image_files:
#     path = "people/" + filename
#     print("Processing:", path)

#     # Load image
#     img = image.Image(path, copy_to_fb=True)


#     # Resize to model input shape
#     # resized = img.resize(w, h)
#     # gray_img = img.to_grayscale()
#     # resized = img.copy(roi=(0, 0, 96, 96))  # Crop to top-left 96x96

#     x_offset = (img.width() - w) // 2
#     y_offset = (img.height() - h) // 2
#     resized = img.copy(roi=(x_offset, y_offset, w, h))

#     # Run model (classification)
#     result = model.predict([resized])[0].flatten().tolist()
#     labels = model.labels

#     # Get best label and score
#     # scores = sorted(zip(labels, result), key=lambda x: x[1], reverse=True)
#     # label, confidence = scores[0]
#     label, confidence = sorted(zip(model.labels, result), key=lambda x: x[1], reverse=True)[0]
#     print("Detected:", label, "Confidence:", confidence)

#     # If person detected with high confidence, draw text and save
#     # if label == "person" and confidence > 0.5:
#     #     # Ensure image is in RGB565 so we can draw colored text
#     #     if img.format() != image.RGB565:
#     #         img = img.to_rgb565()
#     #     # img.draw_string(10, 10, "PERSON", color=(255, 0, 0), scale=2)

#     #     # Draw bounding box around the detected person
#     #     x, y, w, h = out.rect()
#     #     img.draw_rectangle(x, y, w, h, color=(255, 0, 0), thickness=2)

#         # If person detected with high confidence, use sliding window to locate
#     if label == "person" and confidence > 0.5:
#         if img.format() != image.RGB565:
#             img = img.to_rgb565()

#         tile_w = 96
#         tile_h = 96
#         stride = 20  # Smaller = more accurate, but slower

#         for y in range(0, img.height() - tile_h + 1, stride):
#             for x in range(0, img.width() - tile_w + 1, stride):
#                 tile = img.copy(roi=(x, y, tile_w, tile_h))
#                 tile_result = model.predict([tile])[0].flatten().tolist()
#                 tile_label, tile_conf = sorted(zip(model.labels, tile_result), key=lambda x: x[1], reverse=True)[0]

#                 if tile_label == "person" and tile_conf > 0.7:
#                     img.draw_rectangle(x, y, tile_w, tile_h, color=(255, 0, 0), thickness=2)
#                     log_detection(filename, tile_conf, x, y, tile_w, tile_h)



#     # Save to /processed folder regardless
#     save_path = "processed/" + filename
#     img.save(save_path)
#     print("Saved:", save_path)



# print("Finished all images.")


import sensor, image, time, os
import ml

log_path = "log.txt"

def log_detection(filename, confidence, x, y, w, h):
    with open(log_path, "a") as f:
        line = "File: {}, Confidence: {:.2f}, BBox: ({}, {}, {}, {})\n".format(
            filename, confidence, x, y, w, h)
        f.write(line)

# Load person classification model
model = ml.Model("/rom/person_detect.tflite")

# Ensure /processed directory exists
if not "processed" in os.listdir():
    os.mkdir("processed")

# Get expected input size from model
input_shape = model.input_shape[0]  # Should be (1, 96, 96, 1)
_, h, w, _ = input_shape
print("Model expects input size:", w, "x", h)

# Check and get image list
if "people" not in os.listdir():
    raise OSError("Directory /people not found. Please create it on the SD card.")

image_files = [f for f in os.listdir("people") if f.endswith((".jpg", ".bmp", ".png"))]

for filename in image_files:
    path = "people/" + filename
    print("Processing:", path)

    img = image.Image(path, copy_to_fb=True)

    x_offset = (img.width() - w) // 2
    y_offset = (img.height() - h) // 2
    resized = img.copy(roi=(x_offset, y_offset, w, h))

    result = model.predict([resized])[0].flatten().tolist()
    label, confidence = sorted(zip(model.labels, result), key=lambda x: x[1], reverse=True)[0]
    print("Detected:", label, "Confidence:", confidence)

    if label == "person" and confidence > 0.5:
        if img.format() != image.RGB565:
            img = img.to_rgb565()

        tile_w, tile_h = w, h
        stride = 30

        best_conf = 0
        best_box = None

        for y in range(0, img.height() - tile_h + 1, stride):
            for x in range(0, img.width() - tile_w + 1, stride):
                tile = img.copy(roi=(x, y, tile_w, tile_h))
                tile_result = model.predict([tile])[0].flatten().tolist()
                tile_label, tile_conf = sorted(zip(model.labels, tile_result), key=lambda x: x[1], reverse=True)[0]

                if tile_label == "person" and tile_conf > best_conf:
                    best_conf = tile_conf
                    best_box = (x, y, tile_w, tile_h)

        if best_box and best_conf > 0.7:
            x, y, w, h = best_box
            img.draw_rectangle(x, y, w, h, color=(255, 0, 0), thickness=2)
            log_detection(filename, best_conf, x, y, w, h)

    # Save processed image
    save_path = "processed/" + filename
    img.save(save_path)
    print("Saved:", save_path)

print("Finished all images.")
