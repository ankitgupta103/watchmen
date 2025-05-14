import constants

from vyomcloudbridge.services import queue_writer_json

class Communicator:
    def __init__(self, device_type, device_idstr):
        self.device_type = constants.DEVICE_TYPE_CAM
        self.device_idstr = device_idstr
        self.device_id = 0
        self.writer = queue_writer_json.QueueWriterJson()
        self.gps = "5.8833, -162.0833"

    def register(self):
        if self.device_type is not constants.DEVICE_TYPE_CAM:
            return
        register_msg = {
                "device_idstr" : self.device_idstr,
                "distance_cc" : -1,
                "lat" : self.gps,
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
    comm = Communicator(constants.DEVICE_TYPE_CAM, "xyz")
    comm.register()
    comm.send_heartbeat(5)

if __name__=="__main__":
    main()
