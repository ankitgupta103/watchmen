YOLOMODELNAME="yolov8n.pt"

DEVICE_TYPE_CAM = "CAMUNIT"
DEVICE_TYPE_COMMAND = "COMMAND"

# Device IDs which act as CAM start with this
DEVICE_ID_CAM_BASE = 1000000
# Device IDs which act as Command Center start with this
DEVICE_ID_CC_BASE = 1000

# No conflict please
MESSAGE_TYPE_SPATH = "S"
MESSAGE_TYPE_SCAN = "C"
MESSAGE_TYPE_HEARTBEAT = "H"
MESSAGE_TYPE_PHOTO = "P"
MESSAGE_TYPE_ACK = "A"
MESSAGE_TYPE_NACK_CHUNK = "N"
MESSAGE_TYPE_CHUNK_BEGIN = "B"
MESSAGE_TYPE_CHUNK_ITEM = "I"
MESSAGE_TYPE_CHUNK_END = "E"

JK_MESSAGE_TYPE = "mst"
JK_SOURCE = "src"
JK_LAST_SENDER = "l_s"
JK_SOURCE_TIMESTAMP = "sts"
JK_NEIGHBOURS = "nei"
JK_IMAGE_COUNT = "imc"
JK_EVENT_COUNT = "evc"
JK_SHORTEST_PATH = "shp"
JK_DEST = "dst"
JK_PATH_SO_FAR = "psf"
JK_LAST_TS = "lts"
JK_IMAGE_DATA = "imd"
JK_IMAGE_TS = "its"

JK_NETWORK_ID = "nid"

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

NO_DEST = "X"

# 0 is an error here
HN_ID = {
        "central" : "A",
        "rpi2" : "B",
        "rpi3" : "C"
        "rpi4" : "D"
        }

# First has camera,
# Last is CC
# Everything in between is passthrough.
PATH_DEMOB = ["D", "C", "B", "A"]
