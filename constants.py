YOLOMODELNAME="yolov8n.pt"

DEVICE_TYPE_CAM = "CAMUNIT"
DEVICE_TYPE_COMMAND = "COMMAND"

# Device IDs which act as CAM start with this
DEVICE_ID_CAM_BASE = 1000000
# Device IDs which act as Command Center start with this
DEVICE_ID_CC_BASE = 1000

MESSAGE_TYPE_SPATH = "SPath"
MESSAGE_TYPE_SCAN = "Scan"
MESSAGE_TYPE_HEARTBEAT = "Heartbeat"

MESSAGE_TYPE_PHOTO = "Photo"

PRIORITY_LOW = 1
PRIORITY_HIGH = 2

RPI_SERIAL_FILENAME = "/sys/firmware/devicetree/base/serial-number"

node_layout = [
        ["R", "Q", "P", "O", "N"],
        ["S", "F", "E", "D", "M"],
        ["T", "G", "A", "C", "L"],
        ["U", "H", "I", "B", "K"],
        ["V", "W", "X", "Y", "J", "Z"]
        ]
