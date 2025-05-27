YOLOMODELNAME="yolov8n.pt"

DEVICE_TYPE_CAM = "CAMUNIT"
DEVICE_TYPE_COMMAND = "COMMAND"

# Device IDs which act as CAM start with this
DEVICE_ID_CAM_BASE = 1000000
# Device IDs which act as Command Center start with this
DEVICE_ID_CC_BASE = 1000

MESSAGE_TYPE_SPATH = "sp"
MESSAGE_TYPE_SCAN = "sc"
MESSAGE_TYPE_HEARTBEAT = "hb"
MESSAGE_TYPE_PHOTO = "ph"
MESSAGE_TYPE_ACK = "ak"

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
