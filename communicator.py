import constants
import device_info

from vyomcloudbridge.services import queue_writer_json

class Communicator:
    def __init__(self):
        self.writer = queue_writer_json.QueueWriterJson()

    def register(self, dinfo):
        if dinfo.device_type is not constants.DEVICE_TYPE_CAM:
            return
        register_msg = {
                "device_idstr" : dinfo.device_id_str,
                "distance_cc" : -1,
                "lat" : dinfo.gps,
                }

        (succ, err) = self.writer.write_message(
                message_data=register_msg,
                data_type="json",
                data_source="register",
                destination_ids=["1001"],
                mission_id="1234",
                priority=1,
                )
        print("Register sent")
        print(succ)
        print(err)

    def send_heartbeat(self, ts):
        return []

def main():
    dinfo = device_info.DeviceInfo("9eccfdf8c851a5ef")
    comm = Communicator()
    comm.register(dinfo)
    comm.send_heartbeat(5)

if __name__=="__main__":
    main()
