JK_MESSAGE_TYPE = "message_type"
JK_SOURCE = "source"
JK_DEST = "dest"
JK_LAST_SENDER = "last_sender"
JK_LAST_TS = "last_ts"
JK_SOURCE_TIMESTAMP = "source_timestamp"
JK_SHORTEST_PATH = "shortest_path"
JK_PATH_SO_FAR = "path_so_far"
JK_NEIGHBOURS = "neighbours"
JK_IMAGE_COUNT = "image_count"
JK_EVENT_COUNT = "event_count"
JK_IMAGE_DATA = "image_data"
JK_IMAGE_TS = "image_ts"

# Message Types
MESSAGE_TYPE_SCAN = "scan"
MESSAGE_TYPE_SPATH = "spath"
MESSAGE_TYPE_HEARTBEAT = "heartbeat"
MESSAGE_TYPE_PHOTO = "photo"
LOG_MESSAGE = "log_message" # New message type for logging

# The network layout grid
node_layout = [
    ["R", "Q", "P", "O", "N"],
    ["S", "F", "E", "D", "M"],
    ["T", "G", "A", "C", "L"],
    ["U", "H", "I", "B", "K"],
    ["V", "W", "X", "Y", "J"]
]

# Command Central Node ID
CENTRAL_NODE_ID = "ZZZ"