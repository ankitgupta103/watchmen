import time
import os
import io
import threading
from picamera2 import Picamera2
from PIL import Image
from threading import Thread, Event


class CameraController:
    def _init_(self, fps=10, quality=75, output_dir="captures"):
        """
        Initialize the camera controller.

        Args:
            fps (int): Frames per second (5-20)
            quality (int): JPEG quality (1-100)
            output_dir (str): Output directory for captures
        """
        self.fps = fps
        self.quality = quality
        self.output_dir = output_dir
        self.picam2 = None
        self.capture_thread = None
        self.stop_event = Event()
        self.frame_count = 0
        self._lock = threading.RLock()  # Lock for thread safety
        self.camera_initialized = False

        # Initialize camera once during class initialization
        self._initialize_camera()

    def _initialize_camera(self):
        """
        Initialize and configure the camera.

        This method attempts to initialize the camera only if it's not already initialized.
        The camera remains initialized for the lifetime of the application.

        Raises:
            RuntimeError: If camera initialization fails after all attempts.
        """
        with self._lock:
            # Skip if camera is already initialized
            if self.camera_initialized and self.picam2 is not None:
                return

            try:
                # Check for available cameras first
                camera_info = Picamera2.global_camera_info()
                if not camera_info:
                    print("No camera detected in global_camera_info.")
                    print("Attempting to initialize camera directly...")

                # Try to initialize the camera with standard approach
                self.picam2 = Picamera2()

                # Configure video parameters
                config = self.picam2.create_video_configuration(
                    main={"size": (1280, 720)}, controls={"FrameRate": self.fps}
                )
                self.picam2.configure(config)
                self.camera_initialized = True
                print("Camera initialized successfully!")

            except Exception as e:
                print(f"Error initializing camera: {e}")
                # Try alternative approach for cameras at non-standard paths
                try:
                    print("Trying alternative camera initialization...")
                    # Add a small delay before second attempt
                    time.sleep(1)
                    self.picam2 = Picamera2(0)  # Try with index 0
                    config = self.picam2.create_video_configuration(
                        main={"size": (1280, 720)}, controls={"FrameRate": self.fps}
                    )
                    self.picam2.configure(config)
                    self.camera_initialized = True
                    print("Camera initialized with alternative method.")
                except Exception as e2:
                    print(f"Alternative initialization also failed: {e2}")
                    self.camera_initialized = False
                    raise RuntimeError(
                        "Failed to initialize camera. Check connection and permissions."
                    )

    def _capture_loop(self):
        """
        Main capture loop running in a separate thread.

        This method continuously captures frames at the specified frame rate
        until stop_event is set. Each frame is saved as a JPEG file in the
        output directory with a timestamp filename.
        """
        print(f"Capture thread started with ID: {threading.get_ident()}")

        try:
            while not self.stop_event.is_set():
                start_time = time.time()

                try:
                    with self._lock:
                        if self.picam2 is None:
                            print(
                                "Camera is no longer available. Exiting capture loop."
                            )
                            break

                        # Capture frame as PIL image
                        image = self.picam2.capture_image()

                    # Convert to JPEG with specified quality
                    jpeg_buffer = io.BytesIO()
                    image.save(jpeg_buffer, format="JPEG", quality=self.quality)
                    jpeg_data = jpeg_buffer.getvalue()

                    # Check file size
                    if len(jpeg_data) > 100 * 1024:  # 100KB
                        print(
                            f"Frame {self.frame_count} too large ({len(jpeg_data)/1024:.1f}KB) - consider reducing quality"
                        )
                        continue

                    # Save frame directly to the output directory, no subfolder
                    filename = os.path.join(
                        self.output_dir, f"{int(time.time() * 1000)}.jpg"
                    )
                    with open(filename, "wb") as f:
                        f.write(jpeg_data)

                    self.frame_count += 1

                    # Maintain frame rate
                    elapsed = time.time() - start_time
                    sleep_time = (1 / self.fps) - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                except Exception as e:
                    print(f"Error in capture loop: {e}")
                    # If we have a critical error, exit the loop
                    if "Camera is not running" in str(e):
                        print("Camera is not running. Exiting capture loop.")
                        break
                    # For other errors, wait a bit and continue
                    time.sleep(0.5)
        finally:
            print(f"Capture thread {threading.get_ident()} exiting")

    def start(self):
        """
        Start capturing frames.

        This method starts the camera if needed and creates a new capture thread.
        It includes checks to prevent multiple captures from running simultaneously.

        Returns:
            bool: True if capture was started successfully, False otherwise.
        """
        with self._lock:
            # Check if already running
            if self.capture_thread and self.capture_thread.is_alive():
                print("Capture is already running")
                return False

            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)

            # Reset state before starting
            self.stop_event.clear()
            self.frame_count = 0

            try:
                # Make sure camera is initialized
                if not self.camera_initialized:
                    self._initialize_camera()

                # Start the camera for capturing
                self.picam2.start()

                # Start capture thread
                self.capture_thread = Thread(
                    target=self._capture_loop, name="CameraCapture"
                )
                self.capture_thread.daemon = True
                self.capture_thread.start()

                print(f"Started capturing to {self.output_dir}")
                return True
            except Exception as e:
                print(f"Failed to start capture: {e}")
                return False

    def stop(self):
        """
        Stop capturing frames but keep the camera initialized.

        This method signals the capture thread to stop and waits for it to finish.
        The camera stays initialized for reuse in subsequent missions.

        Returns:
            bool: True if capture was stopped successfully, False if no capture was running.
        """
        with self._lock:
            if not self.capture_thread or not self.capture_thread.is_alive():
                print("No capture is running")
                return False

            print("Stopping capture loop...")

            # Signal the capture loop to stop
            self.stop_event.set()

        # Release lock while waiting for thread to join
        time.sleep(0.5)

        # Wait for the capture thread to finish (with timeout)
        self.capture_thread.join(timeout=5.0)

        with self._lock:
            # If thread is still alive after timeout, log warning
            if self.capture_thread and self.capture_thread.is_alive():
                print("Warning: Capture thread did not exit cleanly")

            # Stop the camera capture but DON'T release the camera
            if (
                self.picam2
                and hasattr(self.picam2, "_is_running")
                and self.picam2._is_running
            ):
                try:
                    self.picam2.stop()
                    print("Camera capture stopped (camera remains initialized)")
                except Exception as e:
                    print(f"Error stopping camera capture: {e}")

            # Reset thread reference but keep camera initialized
            self.capture_thread = None

            print(f"Captured {self.frame_count} frames to {self.output_dir}")
            return True

    def close(self):
        """
        Completely release camera resources.

        This method should be called when shutting down the application
        to release all camera resources.
        """
        with self._lock:
            # First make sure capture is stopped
            if self.capture_thread and self.capture_thread.is_alive():
                self.stop()

            # Then release camera resources
            if self.picam2:
                try:
                    if hasattr(self.picam2, "_is_running") and self.picam2._is_running:
                        self.picam2.stop()

                    # Explicitly close the camera to release resources
                    self.picam2.close()
                    print("Camera resources fully released")
                except Exception as e:
                    print(f"Error during camera cleanup: {e}")
                finally:
                    # Set to None to allow garbage collection
                    self.picam2 = None
                    self.camera_initialized = False
