import socket
from datetime import datetime
import constants

def get_hostname():
    """Get system hostname"""
    return socket.gethostname()

def get_device_id():
    """Get device ID from hostname"""
    hname = get_hostname()
    if hname not in constants.HN_ID:
        return None
    return constants.HN_ID[hname]

def is_node_src(devid):
    """Check if device is source node"""
    return constants.PATH_DEMOB[0] == devid

def is_node_dest(devid):
    """Check if device is destination node (Command Center)"""
    return constants.PATH_DEMOB[-1] == devid

def is_node_passthrough(devid):
    """Check if device is passthrough node"""
    if is_node_src(devid) or is_node_dest(devid):
        return False
    return True

def get_next_dest(devid):
    """Get next destination in the network path"""
    idx = -1
    num_nodes = len(constants.PATH_DEMOB)
    for i in range(num_nodes):
        if devid == constants.PATH_DEMOB[i]:
            if i + 1 >= num_nodes:
                return None
            else:
                return constants.PATH_DEMOB[i+1]
    return None

def get_time_str():
    """Get formatted time string"""
    t = datetime.now()
    return f"{str(t.hour).zfill(2)}{str(t.minute).zfill(2)}"

def print_system_info(devid, has_camera=False):
    """Print system initialization information"""
    print(f"🚀 Starting Watchmen System")
    print(f"🏷️  Device ID: {devid}")
    print(f"🖥️  Hostname: {get_hostname()}")
    print(f"📁 Image directory: /home/pi/Documents/images")
    print(f"📷 Camera mode: {'ENABLED' if has_camera else 'DISABLED'}")
    print(f"Message Classification:")
    print(f"   ALL images → Suspicious events (with severity based on detections)")
    print(f"   Heartbeats, GPS, Events → Health messages")
    print(f"   System status checks → Health events (every 60 seconds)")
    print(f"Image Upload:")
    print(f"   Images uploaded as files (not base64)")
    print(f"   Image URLs stored in suspicious event data")
    print(f"   Consistent timestamps for related images")