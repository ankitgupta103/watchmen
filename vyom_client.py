from datetime import datetime, timezone
import time
from typing import Union
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson
from vyomcloudbridge.utils.logger_setup import setup_logger
from vyomcloudbridge.utils.configs import Configs
from vyomcloudbridge.utils.common import (
    get_mission_upload_dir
)
from vyomcloudbridge.constants.constants import default_mission_id
import json
import logging

import threading
from vyomcloudbridge.services.root_store import RootStore


class VyomClient:
    def __init__(self, logger=None):
        if logger is not None:
            self.logger = logger
        else:
            try:
                self.logger = setup_logger(
                    name=self.__class__.__module__ + "." + self.__class__.__name__,
                    show_terminal=True,
                )
            except Exception:
                # Fallback to main logger if setup_logger is not available
                self.logger = logging.getLogger("main")
        self.writer = QueueWriterJson()
        self.machine_config = Configs.get_machine_config()
        self.machine_id = self.machine_config.get("machine_id", "-") or "-"
        self.organization_id = self.machine_config.get("organization_id", "-") or "-"
        self.HN_TO_VYOM_ID = {
            "rpi6": 201,
            "rpi7": 202,
            "rpi8": 203,
            6: 201,
            7: 202,
            8: 203,
        }
        self.expiration_time = 5000  # milisecond
        self.location_cache = {}  # Cache for last known location per node

        try:
            self.root_store = RootStore()
            self.logger.info("RootStore instantiated successfully in VyomClient __init__.")
        except Exception as e:
            self.logger.error(f"Error instantiating RootStore in VyomClient __init__: {e}", exc_info=True)
            self.root_store = None # Handle case where it fails

    def on_image_arrive(
        self,
        node_hn: str,
        image: bytes,
        filename: str = None,
        timestamp: str = None,
    ):
        """_summary_
        Args:
            node_hn (str): hostname of device
            image (bytes): image in bytes format
            timestamp (str, optional): timestamp string in iso format, in UTC timezone
            filename (str, optional): filename of the image which will saved to s3 and fetch with that na,e
        """
        try:
            if not node_hn in self.HN_TO_VYOM_ID:
                self.logger.error(
                    f"error in on_image_arrive, Node {node_hn} not found in HN_TO_VYOM_ID"
                )
                return
            vyom_machine_id = self.HN_TO_VYOM_ID[node_hn]

            if filename is None:
                epoch_ms = int(time.time() * 1000)
                filename = f"{epoch_ms}.jpg"
            else:
                if not filename.endswith(".jpg") and not filename.endswith(".jpeg"):
                    filename = filename.split(".")[0]
                    filename = f"{filename}.jpg"

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
            self.logger.error(f"Error setting location in VyomClient: {e}")

    # TODO: Add event severity to the payload
    def on_event_arrive(
        self,
        node_hn: str,
        event_id: str = None,
        timestamp: str = None,
        eventstr: str = None,
        event_severity: str = None,
        meta: dict = None,
    ):
        """_summary_

        Args:
            node_hn (str): _description_
            timestamp (str, optional): _description_. Defaults to None.
            event_id (str, optional): _description_. Defaults to None.
        """
        try:
            if not node_hn in self.HN_TO_VYOM_ID:
                self.logger.error(
                    f"error in on_event_arrive, Node {node_hn} not found in HN_TO_VYOM_ID"
                )
                return
            vyom_machine_id = self.HN_TO_VYOM_ID[node_hn]
            file_s3_dir: str = get_mission_upload_dir(
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
                "event_severity": event_severity,
                "meta": meta,
            }

            self.logger.info(f"[on_event_arrive] Payload: {payload}")
            
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
            self.logger.error(f"Error setting location in VyomClient: {e}")

    def on_hb_arrive(
        self,
        node_hn: str,
        lat: Union[int, float] = None,
        long: Union[int, float] = None,
        timestamp: str = None,
    ):
        """
        timestamp: str = None, lat: int=None, long: int=None
        """
        location = None
        health_status = 0 # 0: Offline, 1: Healthy, 2: Maintenance 

        self.logger.info(f"[on_hb_arrive] Called with node_hn={node_hn}, lat={lat}, long={long}, timestamp={timestamp}")
        try:
            if not node_hn in self.HN_TO_VYOM_ID:
                self.logger.error(
                    f"error in on_event_arrive, node {node_hn} not found in HN_TO_VYOM_ID"
                )
                return
            vyom_machine_id = self.HN_TO_VYOM_ID[node_hn]
            epoch_ms = int(time.time() * 1000)

            if timestamp is None:
                timestamp = datetime.now(timezone.utc).isoformat()
            self.logger.debug(f"[on_hb_arrive] Using timestamp: {timestamp}")

            cached_location = self.location_cache.get(node_hn)
            self.logger.debug(f"[on_hb_arrive] Cached location for {node_hn}: {cached_location}")
            if cached_location is None:
                cached_location =  {"lat": None, "long": None, "timestamp": epoch_ms}
                            
            new_location = None
            if lat is not None and long is not None:
                new_location = {"lat": lat, "long": long, "timestamp": epoch_ms}
                self.logger.debug(f"[on_hb_arrive] New location provided: {new_location}")

            if new_location:
                self.location_cache[node_hn] = new_location
                location = new_location
                health_status = 1 # Healthy
            elif cached_location:
                self.logger.info(f"[on_hb_arrive] No new location, using cached for {node_hn}.")
                location = cached_location
                health_status = 1
            else:
                self.logger.info(f"[on_hb_arrive] No location data available for {node_hn}, setting to Maintenance.")
                health_status = 2 # Maintenance

            payload = {
                "machine_id": vyom_machine_id,
                "buffer": 0,
                "data_size": 0,
                "data_size_uploaded": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": epoch_ms,
                "location": location,
                "health": health_status,
            }

            filename = f"{epoch_ms}.json"

            self.logger.info(f"[on_hb_arrive] Sending machine stats payload: {payload}")

            self.writer.write_message(
                message_data=payload,
                data_type="json",
                data_source="machine_stats",
                destination_ids=["s3"],
                source_id=vyom_machine_id,
                filename=filename,
                priority=3,
                expiry_time=self.expiration_time,
            )

            self.logger.debug(f"[on_hb_arrive] Finished sending payload for {node_hn}.")

        except Exception as e:
            self.logger.error(f"Error setting location in VyomClient: {e}")


    def _send_central_unit_hb(self, lat: Union[int, float], long: Union[int, float]):
        """
        Helper function to send central unit heartbeat data to RootStore.
        This function will be run in a separate thread.
        """
        if self.root_store is None:
            self.logger.error("RootStore instance is not available. Cannot send central unit heartbeat.")
            return

        try:
            # --- CHANGE: Use the pre-instantiated self.root_store ---
            store = self.root_store 
            # --------------------------------------------------------

            epoch_ms = int(time.time() * 1000)
            location = {"lat": lat, "long": long, "timestamp": epoch_ms}
            health = {"status": 1, "message": "Healthy"}

            self.logger.info(f"Storing central unit location: {location}")
            store.set_data("location", location)
            self.logger.info(f"Storing central unit health: {health}")
            store.set_data("health", health)
            store.cleanup()
            self.logger.info("Central unit heartbeat data sent to RootStore.")
        except Exception as e:
            self.logger.error(f"Error sending central unit heartbeat to RootStore: {e}", exc_info=True)

    def on_central_unit_hb_arrive(self, lat: Union[int, float], long: Union[int, float]):
        """
        Function to handle heartbeat from the central unit.
        It will send the GPS lat and long to the RootStore on a different thread.
        """
        self.logger.info(f"[on_central_unit_hb_arrive] Called with lat={lat}, long={long}")
        # Make sure the target is correct: self._send_central_unit_hb
        hb_thread = threading.Thread(target=self._send_central_unit_hb, args=(lat, long,))
        hb_thread.start()


    def cleanup(self):
        try:
            self.writer.cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up VyomClient: {e}")


if __name__ == "__main__":
    try:
        client = VyomClient()
        import requests
        import time

        client.logger.info("Starting examples")
        # test on_image_arrive
        image_url = "https://sample-videos.com/img/Sample-jpg-image-50kb.jpg"
        response = requests.get(image_url)
        if response.status_code == 200:
            binary_data = response.content
            time.sleep(1)
            client.on_image_arrive(
                node_hn="central", image=binary_data, filename="test_full.jpg"
            )
        else:
            client.logger.error(
                f"[Error] Failed to download {image_url} (Status: {response.status_code})"
            )

        # test on_event_arrive
        client.on_event_arrive(node_hn="rpi3", event_id="test_bb.jpg")

        # test on_hb_arrive
        client.on_hb_arrive(node_hn="rpi4", lat=75.66666, long=73.0589455)


        # test on_central_unit_hb_arrive
        client.on_central_unit_hb_arrive(lat=76.987934, long=76.937954)
        # Give the thread some time to execute
        time.sleep(2) 


    except Exception as e:
        client.logger.error(f"Getting Error in running examples: {str(e)}")
    finally:
        client.cleanup()
    client.logger.info("Starting examples")
