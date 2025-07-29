import os
import sys
import ujson as json  # MicroPython uses 'ujson' for JSON operations
import urequests  # MicroPython uses 'urequests' for HTTP requests

from constants import (
    VYOM_ROOT_DIR,
    MACHINE_CONFIG_FILE,
    MACHINE_REGISTER_API_URL,
    WATCHMEN_ORGANIZATION_ID,
)


def register_machine(interactive=True):
    """
    Register a watchmen device with VyomIQ using MicroPython libraries.

    Args:
        interactive (bool): Whether to run in interactive mode and prompt for input.

    Returns:
        tuple: (success: bool, error: str)
    """
    print("\n=== Watchmen Device Registration (MicroPython) ===\n")

    # Check if config file already exists
    try:
        # In MicroPython, os.stat is a reliable way to check for file existence.
        os.stat(MACHINE_CONFIG_FILE)
        config_exists = True
    except OSError:
        config_exists = False

    if config_exists:
        print(f"Configuration file already exists at: {MACHINE_CONFIG_FILE}")
        try:
            # Read existing configuration
            with open(MACHINE_CONFIG_FILE, "r") as f:
                config = json.load(f)

            machine_info = config.get("MACHINE")
            if machine_info:
                machine_id = machine_info.get("machine_id", "Unknown")
                machine_uid = machine_info.get("machine_uid", "Unknown")
                machine_name = machine_info.get("machine_name", "Unknown")

                print("\n--- Existing Device Details ---")
                print(f"Machine ID: {machine_id}")
                print(f"Machine UID: {machine_uid}")
                print(f"Machine Name: {machine_name}")

                if interactive:
                    overwrite = (
                        input("\nDevice already registered. Overwrite? [y/N]: ")
                        .strip()
                        .lower()
                    )
                    if overwrite not in ["y", "yes"]:
                        print("Registration cancelled.")
                        return True, ""
                else:
                    print("Device already registered. Skipping registration.")
                    return True, ""
            else:
                print(
                    "Warning: Configuration file exists but appears to be invalid. Re-registering..."
                )
        except Exception as e:
            print(f"Error reading configuration file: {str(e)}")
            print("Re-registering...")
    else:
        print("No configuration file found. Starting registration...")

    # Get device registration information
    if interactive:
        machine_uid = input("Device UID: ").strip()
        machine_name = input("Device Name: ").strip()
    else:
        # For non-interactive mode on microcontrollers, we use hardcoded defaults
        # as there are no environment variables.
        machine_uid = "watchmen-device-01"
        machine_name = "Watchmen Device (Auto)"
        print(
            f"Non-interactive mode: Using default UID '{machine_uid}' and Name '{machine_name}'"
        )

    if not machine_uid or not machine_name:
        return False, "Device UID and Device Name are required"

    # Create payload JSON
    payload = {
        "name": machine_name,
        "machine_uid": machine_uid,
        "organization_id": WATCHMEN_ORGANIZATION_ID,
    }

    # Make API call to register device
    print("Registering device with VyomIQ...")
    response = None
    try:
        # urequests.post is the equivalent of requests.post
        response = urequests.post(
            MACHINE_REGISTER_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        # Check response
        if response.status_code == 200:
            data = response.json()  # .json() is also available in urequests
            if data.get("status") == 200:
                print("Device registration successful!")

                # Create directory if it doesn't exist.
                # os.makedirs is not in MicroPython, so we create one level.
                try:
                    os.mkdir(VYOM_ROOT_DIR)
                except OSError as e:
                    # Error code 17 means directory already exists, which is fine.
                    if e.args[0] != 17:
                        raise

                # Prepare configuration data using a standard Python dictionary
                config_data = {}
                machine_data = data.get("data", {})
                config_data["MACHINE"] = {
                    "machine_id": str(machine_data.get("id", "")),
                    "machine_uid": machine_data.get("machine_uid", ""),
                    "machine_name": machine_data.get("name", ""),
                    "machine_model_id": str(machine_data.get("machine_model", "")),
                    "machine_model_name": machine_data.get("machine_model_name", ""),
                    "machine_model_type": machine_data.get("machine_model_type", ""),
                    "organization_id": str(machine_data.get("current_owner", "")),
                    "organization_name": machine_data.get("current_owner_name", ""),
                    "created_at": machine_data.get("created_at", ""),
                    "updated_at": machine_data.get("updated_at", ""),
                    "session_id": machine_data.get("session_id", ""),
                }

                # Save IoT credentials if present
                if "iot_data" in machine_data:
                    iot_data = machine_data["iot_data"]
                    config_data["IOT"] = {
                        "thing_name": iot_data.get("thing_name"),
                        "thing_arn": iot_data.get("thing_arn"),
                        "policy_name": iot_data.get("policy_name"),
                        "certificate": iot_data.get("certificate", {}).get(
                            "certificatePem"
                        ),
                        "private_key": iot_data.get("certificate", {})
                        .get("keyPair", {})
                        .get("PrivateKey"),
                        "public_key": iot_data.get("certificate", {})
                        .get("keyPair", {})
                        .get("PublicKey"),
                        "root_ca": iot_data.get("root_ca"),
                    }

                # Save configuration as a JSON file
                with open(MACHINE_CONFIG_FILE, "w") as f:
                    json.dump(config_data, f)

                print(f"Configuration saved to {MACHINE_CONFIG_FILE}")
                print(f"Device Model ID: {machine_data.get('machine_model', 'N/A')}")

                return True, ""
            else:
                error_msg = f"Registration failed with status: {data.get('status')}"
                print(f"Error: {error_msg}")
                print(f"Response: {data}")
                return False, error_msg
        else:
            error_msg = f"HTTP error {response.status_code}: {response.text}"
            print(f"Error: {error_msg}")
            return False, error_msg

    except OSError as e:
        # OSError is the common exception for network errors in MicroPython
        error_msg = f"Network or File I/O error during registration: {e}"
        print(f"Error: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during registration: {str(e)}"
        print(f"Error: {error_msg}")
        return False, error_msg
    finally:
        # Ensure the response is closed to free up memory
        if response:
            response.close()


def setup(interactive=True):
    """
    Perform the minimal Watchmen device setup process.

    Args:
        interactive (bool): Whether to run in interactive mode and prompt for input

    Returns:
        bool: True if setup completed successfully, False otherwise
    """
    print("\n=== Starting Watchmen Device Setup (MicroPython) ===\n")

    # Register the device
    registration_success, error = register_machine(interactive=interactive)
    if not registration_success:
        print(f"Device registration failed: {error}")
        return False

    print("\n=== Watchmen Device Setup Completed Successfully ===")
    print(f"Configuration saved to: {MACHINE_CONFIG_FILE}")
    return True


if __name__ == "__main__":
    # Check if script is run with --non-interactive flag
    is_interactive = "--non-interactive" not in sys.argv
    success = setup(interactive=is_interactive)

    # Exit with appropriate status code
    if not success:
        print("Setup failed. Exiting.")
        sys.exit(1)
    else:
        print("Setup successful.")
