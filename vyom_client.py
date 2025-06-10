from datetime import datetime, timezone
import time
from typing import Union
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson
from vyomcloudbridge.utils.logger_setup import setup_logger
from vyomcloudbridge.utils.configs import Configs
from vyomcloudbridge.utils.common import (
    get_mission_upload_dir,
    get_mission_dir_for_s3,
    get_data_upload_dir,
    get_data_dir_for_s3,
)
from vyomcloudbridge.constants.constants import default_mission_id


class VyomClient:
    def __init__(self):
        self.logger = setup_logger(
            name=self.__class__.__module__ + "." + self.__class__.__name__,
            show_terminal=False,
        )
        self.writer = QueueWriterJson()
        self.machine_config = Configs.get_machine_config()
        self.machine_id = self.machine_config.get("machine_id", "-") or "-"
        self.organization_id = self.machine_config.get("organization_id", "-") or "-"
        self.HN_TO_VYOM_ID = {"central": 197, "rpi2": 198, "rpi3": 200, "rpi4": 199}
        self.expiration_time = 2000  # milisecond

    def on_image_arrive(
        self,
        node_hn: str,
        image: bytes,
        event_id: str = None,
        timestamp: str = None,
    ):
        """_summary_
        Args:
            node_hn (str): hostname of device
            image (bytes): image in bytes format
            timestamp (str, optional): timestamp string in iso format, in UTC timezone
            event_id (str, optional): event_id of the image which will saved to s3 and fetch with that na,e
        """
        try:
            if not node_hn in self.HN_TO_VYOM_ID:
                self.logger.error(f"Node {node_hn} not found in HN_TO_VYOM_ID")
                return
            vyom_machine_id = self.HN_TO_VYOM_ID[node_hn]

            if event_id is None:
                epoch_ms = int(time.time() * 1000)
                filename = f"{epoch_ms}.jpg"
            elif not event_id.endswith(".jpg"):
                filename = event_id.split(".")[0]
                filename = f"{event_id}.jpg"

            self.writer.write_message(
                message_data=image,
                data_type="image",
                data_source="IMAGE",
                destination_ids=["s3"],
                source_id=vyom_machine_id,
                filename=filename,
                priority=1,
                merge_chunks=True,
            )
        except Exception as e:
            print(f"Error setting location in VyomClient: {e}")

    def on_event_arrive(
        self,
        node_hn: str,
        event_id: str = None,
        timestamp: str = None,
    ):
        """_summary_

        Args:
            node_hn (str): _description_
            timestamp (str, optional): _description_. Defaults to None.
            event_id (str, optional): _description_. Defaults to None.
        """
        try:
            if not node_hn in self.HN_TO_VYOM_ID:
                self.logger.error(f"Node {node_hn} not found in HN_TO_VYOM_ID")
                return
            vyom_machine_id = self.HN_TO_VYOM_ID[node_hn]
            file_s3_dir: str = get_mission_dir_for_s3(
                organization_id=self.organization_id,  # assuming same organisation for all machines
                machine_id=vyom_machine_id,
                mission_id=default_mission_id,
                data_source="IMAGE",
            )
            try:
                base_filename = event_id.split(".")[0]
            except Exception as e:
                base_filename = event_id

            try:
                file_ext = event_id.split(".")[1]
            except Exception as e:
                file_ext = "jpg"

            filename1 = f"{base_filename}_c.{file_ext}"
            filename2 = f"{base_filename}_f.{file_ext}"

            payload = {
                "image_c_key": f"{file_s3_dir}/{filename1}",
                "image_f_key": f"{file_s3_dir}/{filename2}",
            }
            epoch_ms = int(time.time() * 1000)
            filename = f"{epoch_ms}.json"
            self.writer.write_message(
                message_data=payload,
                data_type="json",
                data_source="EVENT",
                destination_ids=["s3"],
                source_id=vyom_machine_id,
                filename=filename,
                priority=3,
                expiry_time=self.expiration_time,
                merge_chunks=True,
                send_live=True,
            )
        except Exception as e:
            print(f"Error setting location in VyomClient: {e}")

    def on_hb_arrive(
        self, node_hn: str, lat: int = None, long: int = None, timestamp: str = None
    ):
        """
        timestamp: str = None, lat: int=None, long: int=None
        """
        try:
            if not node_hn in self.HN_TO_VYOM_ID:
                self.logger.error(f"Node {node_hn} not found in HN_TO_VYOM_ID")
                return
            vyom_machine_id = self.HN_TO_VYOM_ID[node_hn]

            if timestamp is None:
                timestamp = datetime.now(timezone.utc).isoformat()
            if lat is None or long is None:
                location = None
            else:
                location = {"lat": lat, "long": long, "timestamp": timestamp}

            payload = {
                "machine_id": vyom_machine_id,
                "buffer": 0,
                "data_size": 0,
                "data_size_uploaded": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "location": location,
                # "health": {"status": 1, "message": ""},
                "health": None,
            }

            epoch_ms = int(time.time() * 1000)
            filename = f"{epoch_ms}.json"

            self.writer.write_message(
                message_data=payload,
                data_type="json",
                data_source="machine_state",
                destination_ids=["s3"],
                source_id=vyom_machine_id,
                filename=filename,
                priority=3,
                expiry_time=self.expiration_time,
            )
        except Exception as e:
            print(f"Error setting location in VyomClient: {e}")

    def cleanup(self):
        try:
            self.writer.cleanup()
        except Exception as e:
            print(f"Error cleaning up VyomClient: {e}")


if __name__ == "__main__":
    client = VyomClient()
    import requests
    import time

    try:
        print("Starting examples")
        # test on_image_arrive
        image_url = "https://sample-videos.com/img/Sample-jpg-image-50kb.jpg"
        response = requests.get(image_url)
        if response.status_code == 200:
            binary_data = response.content
            time.sleep(1)
            client.on_image_arrive(
                node_hn="central", image=binary_data, event_id="test_full.jpg"
            )
        else:
            print(
                f"[Error] Failed to download {image_url} (Status: {response.status_code})"
            )

        # test on_event_arrive
        client.on_event_arrive(node_hn="rpi3", event_id="test_bb.jpg")

        # test on_hb_arrive
        client.on_hb_arrive(node_hn="rpi4", lat=75.66666, long=73.0589455)
    except Exception as e:
        print("Getting Error in running examples", {str(e)})
    finally:
        client.cleanup()
    print("Starting examples")
