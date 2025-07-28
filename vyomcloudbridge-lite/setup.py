import os
import sys
import configparser
import requests

from constants import (
    VYOM_ROOT_DIR,
    MACHINE_CONFIG_FILE,
    MACHINE_REGISTER_API_URL,
    WATCHMEN_ORGANIZATION_ID,
)


def register_machine(interactive=True):
    """
    Register a watchmen device with VyomIQ

    Args:
        interactive (bool): Whether to run in interactive mode and prompt for input

    Returns:
        tuple: (success: bool, error: str)
    """
    print("\n=== Watchmen Device Registration ===\n")

    # Check if config file already exists
    if os.path.exists(MACHINE_CONFIG_FILE):
        print(f"Configuration file already exists at: {MACHINE_CONFIG_FILE}")
        try:
            # Read existing configuration
            config = configparser.ConfigParser()
            config.read(MACHINE_CONFIG_FILE)

            if "MACHINE" in config:
                machine_id = config["MACHINE"].get("machine_id", "Unknown")
                machine_uid = config["MACHINE"].get("machine_uid", "Unknown")
                machine_name = config["MACHINE"].get("machine_name", "Unknown")

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
        # For non-interactive mode, generate a default name or use environment variables
        machine_uid = os.environ.get("DEVICE_UID", "watchmen-device")
        machine_name = os.environ.get("DEVICE_NAME", "Watchmen Device")

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
    try:
        response = requests.post(
            MACHINE_REGISTER_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Check response
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 200:
                print("Device registration successful!")

                # Create directory if it doesn't exist
                os.makedirs(VYOM_ROOT_DIR, exist_ok=True)

                # Save configuration
                config = configparser.ConfigParser()
                config["MACHINE"] = {
                    "machine_id": str(data["data"].get("id", "")),
                    "machine_uid": data["data"].get("machine_uid", ""),
                    "machine_name": data["data"].get("name", ""),
                    "machine_model_id": str(data["data"].get("machine_model", "")),
                    "machine_model_name": data["data"].get("machine_model_name", ""),
                    "machine_model_type": data["data"].get("machine_model_type", ""),
                    "organization_id": str(data["data"].get("current_owner", "")),
                    "organization_name": data["data"].get("current_owner_name", ""),
                    "created_at": data["data"].get("created_at", ""),
                    "updated_at": data["data"].get("updated_at", ""),
                    "session_id": data["data"].get("session_id", ""),
                }

                # Save IoT credentials if present
                if "iot_data" in data["data"]:
                    iot_data = data["data"]["iot_data"]
                    config["IOT"] = {
                        "thing_name": iot_data["thing_name"],
                        "thing_arn": iot_data["thing_arn"],
                        "policy_name": iot_data["policy_name"],
                        "certificate": iot_data["certificate"]["certificatePem"],
                        "private_key": iot_data["certificate"]["keyPair"]["PrivateKey"],
                        "public_key": iot_data["certificate"]["keyPair"]["PublicKey"],
                        "root_ca": iot_data["root_ca"],
                    }

                with open(MACHINE_CONFIG_FILE, "w") as f:
                    config.write(f)

                print(f"Configuration saved to {MACHINE_CONFIG_FILE}")
                print(f"Device Model ID: {data['data'].get('machine_model', 'N/A')}")

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

    except requests.exceptions.Timeout:
        error_msg = "Registration request timed out"
        print(f"Error: {error_msg}")
        return False, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error during registration: {str(e)}"
        print(f"Error: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during registration: {str(e)}"
        print(f"Error: {error_msg}")
        return False, error_msg


def setup(interactive=True):
    """
    Perform the minimal Watchmen device setup process.

    Args:
        interactive (bool): Whether to run in interactive mode and prompt for input

    Returns:
        bool: True if setup completed successfully, False otherwise
    """
    print("\n=== Starting Watchmen Device Setup ===\n")

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
        sys.exit(1)
