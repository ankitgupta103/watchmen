# Makefile for USB Hub Power Control - Raspbian Bookworm

# Configuration - Change this to target different hubs
# Based on 'sudo uhubctl' output, your audio device is on hub 3
# Change this value to target different USB hubs
# Note: uhubctl can only control entire hubs, not individual ports
# TARGET_HUB = 1-1 -> Use this to target all the hubs in a 4B or 5B model
TARGET_HUB = 1-1

.PHONY: all shutdown startup full-usb-off full-usb-on hub-shutdown hub-startup list-hubs reset-devices shutdown-all startup-all config

# Default target - provides instructions
all:
	@echo "USB Hub Power Control - Current Configuration:"
	@echo "  TARGET_HUB = $(TARGET_HUB)"
	@echo ""
	@echo "Usage:"
	@echo "  make config       - Show current hub configuration"
	@echo "  make list-hubs    - List all USB hubs and their power control capabilities"
	@echo "  make shutdown     - Powers off USB devices (entire hub $(TARGET_HUB))"
	@echo "  make startup      - Powers on USB devices (entire hub $(TARGET_HUB))"
	@echo "  make reset-devices - Cycle power on hub $(TARGET_HUB)"
	@echo "  make shutdown-all - Powers off ALL USB devices on all hubs"
	@echo "  make startup-all  - Powers on ALL USB devices on all hubs"
	@echo ""
	@echo "Configuration:"
	@echo "  To target a different hub: make shutdown TARGET_HUB=5"
	@echo "  To change permanently: edit TARGET_HUB variable in this Makefile"
	@echo ""
	@echo "Note: uhubctl can only control entire hubs, not individual ports"
	@echo "      This Makefile requires 'sudo' for uhubctl commands."
	@echo "  make full-usb-off   - Guides you to completely disable ALL USB ports (requires reboot)."
	@echo "  make full-usb-on    - Guides you to completely enable ALL USB ports (requires reboot)."

# Target to list all USB hubs and their capabilities
list-hubs:
	@echo "--- Listing all USB hubs and power control capabilities ---"
	sudo uhubctl
	@echo ""
	@echo "Look for hubs that show 'ppps' (per-port power switching supported)"
	@echo "or try controlling specific hubs by number (e.g., -l 3 for hub 3)"

# Show current configuration
config:
	@echo "--- Current Configuration ---"
	@echo "TARGET_HUB = $(TARGET_HUB)"
	@echo ""
	@echo "This means commands will target entire hub $(TARGET_HUB)"
	@echo "To change: edit the TARGET_HUB variable at the top of this Makefile"
	@echo "Or override temporarily: make shutdown TARGET_HUB=5"

# Target to power off USB devices
# Control entire hub since individual port control (3-1 syntax) doesn't work
shutdown:
	@echo "--- Shutting down USB devices ---"
	@echo "Powering off all devices on hub $(TARGET_HUB)..."
	sudo uhubctl -a off -l $(TARGET_HUB)
	@echo "--- USB devices shutdown complete ---"

# Target to power on USB devices  
startup:
	@echo "--- Starting up USB devices ---"
	@echo "Powering on hub $(TARGET_HUB)..."
	sudo uhubctl -a on -l $(TARGET_HUB)
	@echo "--- USB devices startup complete ---"

# Alternative: Try to control specific devices by resetting them
reset-devices:
	@echo "--- Resetting USB devices ---"
	@echo "Cycling power on hub $(TARGET_HUB) (includes audio device)..."
	sudo uhubctl -a cycle -l $(TARGET_HUB)
	@echo "--- Reset complete ---"

# Shutdown all USB devices system-wide
shutdown-all:
	@echo "--- Shutting down ALL USB devices ---"
	@echo "Powering off hub 5..."
	sudo uhubctl -a off -l 5 || echo "Hub 5 control failed"
	@echo "Powering off hub 4..."
	sudo uhubctl -a off -l 4 || echo "Hub 4 control failed"  
	@echo "Powering off hub 3..."
	sudo uhubctl -a off -l 3 || echo "Hub 3 control failed"
	@echo "Powering off hub 2..."
	sudo uhubctl -a off -l 2 || echo "Hub 2 control failed"
	@echo "Powering off hub 1..."
	sudo uhubctl -a off -l 1 || echo "Hub 1 control failed"
	@echo "--- All USB devices shutdown complete ---"

# Startup all USB devices system-wide
startup-all:
	@echo "--- Starting up ALL USB devices ---"
	@echo "Powering on hub 1..."
	sudo uhubctl -a on -l 1 || echo "Hub 1 control failed"
	@echo "Powering on hub 2..."
	sudo uhubctl -a on -l 2 || echo "Hub 2 control failed"
	@echo "Powering on hub 3..."
	sudo uhubctl -a on -l 3 || echo "Hub 3 control failed"
	@echo "Powering on hub 4..."
	sudo uhubctl -a on -l 4 || echo "Hub 4 control failed"
	@echo "Powering on hub 5..."
	sudo uhubctl -a on -l 5 || echo "Hub 5 control failed"
	@echo "--- All USB devices startup complete ---"

# Target to completely disable ALL USB ports (system-wide)
full-usb-off:
	@echo "--- Preparing to disable ALL USB ports system-wide ---"
	@echo "This requires modifying /boot/cmdline.txt and a REBOOT."
	@echo "1. Open the cmdline.txt file for editing:"
	@echo "   sudo nano /boot/cmdline.txt"
	@echo "2. At the end of the SINGLE LINE, add: usbcore.authorized_default=0"
	@echo "   (Example: ... rootwait quiet splash usbcore.authorized_default=0)"
	@echo "3. Save the file (Ctrl+O, Enter) and exit (Ctrl+X)."
	@echo "4. REBOOT your Raspberry Pi for changes to take effect:"
	@echo "   sudo reboot"
	@echo "--- ALL USB ports will be disabled after reboot ---"

# Target to completely enable ALL USB ports (system-wide)
full-usb-on:
	@echo "--- Preparing to enable ALL USB ports system-wide ---"
	@echo "This requires modifying /boot/cmdline.txt and a REBOOT."
	@echo "1. Open the cmdline.txt file for editing:"
	@echo "   sudo nano /boot/cmdline.txt"
	@echo "2. REMOVE 'usbcore.authorized_default=0' from the SINGLE LINE."
	@echo "   (Ensure there are no trailing spaces if it was the last parameter.)"
	@echo "3. Save the file (Ctrl+O, Enter) and exit (Ctrl+X)."
	@echo "4. REBOOT your Raspberry Pi for changes to take effect:"
	@echo "   sudo reboot"
	@echo "--- ALL USB ports will be enabled after reboot ---"

# Legacy targets (may not work on your system)
hub-shutdown:
	@echo "--- Legacy: Attempting to shut down USB hub 1-1 ---"
	@echo "This may not work on your Raspberry Pi model..."
	sudo uhubctl -a off -l 1-1 || echo "ERROR: Hub 1-1 not controllable on this system"

hub-startup:
	@echo "--- Legacy: Attempting to start up USB hub 1-1 ---"
	sudo uhubctl -a on -l 1-1 || echo "ERROR: Hub 1-1 not controllable on this system"
