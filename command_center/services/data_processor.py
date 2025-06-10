import threading
from command_center.utils.abc_service import AbsService


class DataProcessor(AbsService):
    def __init__(self):
        self.image_in_process = set()
        self.is_running = False

    def start_image_processing(self):
        while self.is_running:
            # read all images in the folde
            image = None # read from folder
            # for each image:
            if image not in self.image_in_process:
                self.image_in_process.add(image)

    #       If image not in image_in_process:
    #            add image to  self.image_in_process
    #            if image has corresponding json:
    #       	       event_found, event_detail = classiy_image(image)
    #                ff event_found:
    #                      success: publish_data_to_vyom(image, filename, event_detail)
    #                      If success:
    #                           delete image and json file both,
    #                           remove from the  self.image_in_process
    #                       else:
    #                            remove from self.image_in_process
    #                else:
    #                      delete image and json file both,
    #                      remove from the  self.image_in_process
    #             else:
    # 	         continue
    #        Else:
    # 	 continue: // image already in proccess

    def start(self):
        self.is_running = True
        thread = threading.Thread(target=self.image_processing)
        thread.start()
        

    def stop(self):
        self.is_running = False
    

    
