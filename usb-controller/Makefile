# Makefile for GPIO USB Power Control - Raspbian Bookworm
# Controls USB power via MOSFET switch connected to GPIO

# Configuration
# GPIO pin connected to MOSFET trigger (Physical pin 11 = GPIO 17)
GPIO_PIN = 17
# Delay times in seconds
POWER_ON_DELAY = 2
POWER_OFF_DELAY = 1
CYCLE_DELAY = 3

# GPIO paths
GPIO_PATH = /sys/class/gpio
GPIO_EXPORT = $(GPIO_PATH)/export
GPIO_UNEXPORT = $(GPIO_PATH)/unexport
GPIO_PIN_PATH = $(GPIO_PATH)/gpio$(GPIO_PIN)
GPIO_DIRECTION = $(GPIO_PIN_PATH)/direction
GPIO_VALUE = $(GPIO_PIN_PATH)/value

.PHONY: all shutdown startup cycle-power status setup-gpio setup-gpio-alt cleanup-gpio test-gpio config diagnose

# Default target - provides instructions
all:
	@echo "GPIO USB Power Control - Current Configuration:"
	@echo "  GPIO_PIN = $(GPIO_PIN) (Physical pin 11)"
	@echo "  Power ON  = GPIO HIGH"
	@echo "  Power OFF = GPIO LOW"
	@echo ""
	@echo "Usage:"
	@echo "  make config       - Show current configuration"
	@echo "  make diagnose     - Run GPIO diagnostics"
	@echo "  make setup-gpio   - Initialize GPIO pin for control"
	@echo "  make setup-gpio-alt - Alternative GPIO setup using raspi-gpio"
	@echo "  make status       - Show current GPIO state"
	@echo "  make shutdown     - Turn OFF USB power (GPIO LOW)"
	@echo "  make startup      - Turn ON USB power (GPIO HIGH)"
	@echo "  make cycle-power  - Cycle USB power (OFF->ON)"
	@echo "  make test-gpio    - Test GPIO control (blink pattern)"
	@echo "  make cleanup-gpio - Cleanup GPIO resources"
	@echo ""
	@echo "Configuration:"
	@echo "  To change GPIO pin: make startup GPIO_PIN=18"
	@echo "  To change permanently: edit GPIO_PIN variable in this Makefile"
	@echo ""
	@echo "Hardware Setup:"
	@echo "  - MOSFET VCC    -> Pi Pin 2 (5V)"
	@echo "  - MOSFET Trigger -> Pi Pin 11 (GPIO $(GPIO_PIN))"
	@echo "  - MOSFET controls USB hub power"
	@echo ""
	@echo "Pi 5 Support: Uses pinctrl for GPIO control"
	@echo "Older Pi: Uses raspi-gpio or sysfs interface"

# Show current configuration
config:
	@echo "--- Current Configuration ---"
	@echo "GPIO_PIN = $(GPIO_PIN)"
	@echo "Physical Pin = 11"
	@echo "Power ON Delay = $(POWER_ON_DELAY)s"
	@echo "Power OFF Delay = $(POWER_OFF_DELAY)s"
	@echo "Cycle Delay = $(CYCLE_DELAY)s"
	@echo ""
	@echo "GPIO Control Logic:"
	@echo "  HIGH (1) = USB Power ON"
	@echo "  LOW (0)  = USB Power OFF"

# Setup GPIO pin for output
setup-gpio:
	@echo "--- Setting up GPIO $(GPIO_PIN) for USB power control ---"
	@echo "Checking GPIO interface availability..."
	@if [ ! -d "$(GPIO_PATH)" ]; then \
		echo "ERROR: /sys/class/gpio not available"; \
		echo "Trying alternative raspi-gpio method..."; \
		$(MAKE) setup-gpio-alt; \
		exit 0; \
	fi
	@if [ ! -w "$(GPIO_EXPORT)" ]; then \
		echo "ERROR: Cannot write to $(GPIO_EXPORT)"; \
		echo "Make sure you're running as root: sudo make setup-gpio"; \
		exit 1; \
	fi
	@if [ -d "$(GPIO_PIN_PATH)" ]; then \
		echo "GPIO $(GPIO_PIN) already exported, cleaning up first..."; \
		echo $(GPIO_PIN) > $(GPIO_UNEXPORT) 2>/dev/null || true; \
		sleep 0.5; \
	fi
	@echo "Exporting GPIO $(GPIO_PIN)..."
	@if ! echo $(GPIO_PIN) > $(GPIO_EXPORT); then \
		echo "ERROR: Failed to export GPIO $(GPIO_PIN)"; \
		echo "Trying alternative method..."; \
		$(MAKE) setup-gpio-alt; \
		exit 0; \
	fi
	@echo "Waiting for GPIO to initialize..."
	@sleep 1
	@if [ ! -d "$(GPIO_PIN_PATH)" ]; then \
		echo "ERROR: GPIO $(GPIO_PIN) directory not created"; \
		exit 1; \
	fi
	@echo "Setting GPIO $(GPIO_PIN) as output..."
	@if ! echo "out" > $(GPIO_DIRECTION); then \
		echo "ERROR: Failed to set GPIO direction"; \
		exit 1; \
	fi
	@echo "Initializing GPIO $(GPIO_PIN) to LOW (USB OFF)..."
	@if ! echo "0" > $(GPIO_VALUE); then \
		echo "ERROR: Failed to set GPIO value"; \
		exit 1; \
	fi
	@echo "--- GPIO setup complete ---"

# Alternative GPIO setup using raspi-gpio command or pinctrl (Pi 5)
setup-gpio-alt:
	@echo "--- Setting up GPIO $(GPIO_PIN) using modern GPIO tools ---"
	@if command -v pinctrl >/dev/null 2>&1; then \
		echo "Using pinctrl (Raspberry Pi 5 method)..."; \
		echo "Setting GPIO $(GPIO_PIN) as output with initial LOW state..."; \
		pinctrl set $(GPIO_PIN) op dl; \
		echo "--- pinctrl GPIO setup complete ---"; \
	elif command -v raspi-gpio >/dev/null 2>&1; then \
		echo "Using raspi-gpio method..."; \
		echo "Setting GPIO $(GPIO_PIN) as output with initial LOW state..."; \
		raspi-gpio set $(GPIO_PIN) op dl; \
		echo "--- raspi-gpio GPIO setup complete ---"; \
	else \
		echo "ERROR: Neither pinctrl nor raspi-gpio found"; \
		echo "For Pi 5: pinctrl should be available by default"; \
		echo "For older Pi: install with: sudo apt install raspi-gpio"; \
		exit 1; \
	fi
	@echo "Note: Using modern GPIO method. Some sysfs status commands may not work."

# Show current GPIO status
status:
	@echo "--- GPIO $(GPIO_PIN) Status ---"
	@if command -v raspi-gpio >/dev/null 2>&1; then \
		echo "Using raspi-gpio to check status:"; \
		raspi-gpio get $(GPIO_PIN); \
	fi
	@if [ -d "$(GPIO_PIN_PATH)" ]; then \
		echo "Sysfs GPIO $(GPIO_PIN) is exported"; \
		echo -n "Direction: "; cat $(GPIO_DIRECTION) 2>/dev/null || echo "unknown"; \
		echo -n "Value: "; cat $(GPIO_VALUE) 2>/dev/null || echo "unknown"; \
		VALUE=$(cat $(GPIO_VALUE) 2>/dev/null); \
		if [ "$VALUE" = "1" ]; then \
			echo "USB Power: ON"; \
		elif [ "$VALUE" = "0" ]; then \
			echo "USB Power: OFF"; \
		else \
			echo "USB Power: UNKNOWN"; \
		fi; \
	else \
		echo "Sysfs GPIO $(GPIO_PIN) is not exported"; \
		echo "Using raspi-gpio for status (if available)"; \
	fi

# Turn OFF USB power (try multiple methods)
shutdown:
	@echo "--- Shutting down USB power ---"
	@echo "Setting GPIO $(GPIO_PIN) LOW (USB OFF)..."
	@if [ -d "$(GPIO_PIN_PATH)" ]; then \
		echo "0" > $(GPIO_VALUE) || echo "Sysfs method failed"; \
	fi
	@if command -v pinctrl >/dev/null 2>&1; then \
		pinctrl set $(GPIO_PIN) op dl || echo "pinctrl method failed"; \
	elif command -v raspi-gpio >/dev/null 2>&1; then \
		raspi-gpio set $(GPIO_PIN) op dl || echo "raspi-gpio method failed"; \
	fi
	@sleep $(POWER_OFF_DELAY)
	@echo "--- USB power shutdown complete ---"

# Turn ON USB power (try multiple methods)
startup:
	@echo "--- Starting up USB power ---"
	@echo "Setting GPIO $(GPIO_PIN) HIGH (USB ON)..."
	@if [ -d "$(GPIO_PIN_PATH)" ]; then \
		echo "1" > $(GPIO_VALUE) || echo "Sysfs method failed"; \
	fi
	@if command -v pinctrl >/dev/null 2>&1; then \
		pinctrl set $(GPIO_PIN) op dh || echo "pinctrl method failed"; \
	elif command -v raspi-gpio >/dev/null 2>&1; then \
		raspi-gpio set $(GPIO_PIN) op dh || echo "raspi-gpio method failed"; \
	fi
	@sleep $(POWER_ON_DELAY)
	@echo "--- USB power startup complete ---"

# Cycle USB power (OFF -> ON)
cycle-power:
	@echo "--- Cycling USB power ---"
	@echo "Turning USB power OFF..."
	@if [ -d "$(GPIO_PIN_PATH)" ]; then \
		echo "0" > $(GPIO_VALUE) || echo "Sysfs method failed"; \
	fi
	@if command -v raspi-gpio >/dev/null 2>&1; then \
		raspi-gpio set $(GPIO_PIN) op dl || echo "raspi-gpio method failed"; \
	fi
	@sleep $(CYCLE_DELAY)
	@echo "Turning USB power ON..."
	@if [ -d "$(GPIO_PIN_PATH)" ]; then \
		echo "1" > $(GPIO_VALUE) || echo "Sysfs method failed"; \
	fi
	@if command -v raspi-gpio >/dev/null 2>&1; then \
		raspi-gpio set $(GPIO_PIN) op dh || echo "raspi-gpio method failed"; \
	fi
	@sleep $(POWER_ON_DELAY)
	@echo "--- Power cycle complete ---"

# Test GPIO control with blink pattern
test-gpio:
	@echo "--- Testing GPIO $(GPIO_PIN) control ---"
	@echo "This will blink the USB power 3 times..."
	@for i in 1 2 3; do \
		echo "Blink $i: ON"; \
		if [ -d "$(GPIO_PIN_PATH)" ]; then \
			echo "1" > $(GPIO_VALUE) || echo "Sysfs failed"; \
		fi; \
		if command -v raspi-gpio >/dev/null 2>&1; then \
			raspi-gpio set $(GPIO_PIN) op dh || echo "raspi-gpio failed"; \
		fi; \
		sleep 1; \
		echo "Blink $i: OFF"; \
		if [ -d "$(GPIO_PIN_PATH)" ]; then \
			echo "0" > $(GPIO_VALUE) || echo "Sysfs failed"; \
		fi; \
		if command -v raspi-gpio >/dev/null 2>&1; then \
			raspi-gpio set $(GPIO_PIN) op dl || echo "raspi-gpio failed"; \
		fi; \
		sleep 1; \
	done
	@echo "--- GPIO test complete ---"

# Diagnostic commands
diagnose:
	@echo "--- GPIO Diagnostic Information ---"
	@echo "Kernel version:"
	@uname -r
	@echo ""
	@echo "GPIO interface check:"
	@ls -la /sys/class/gpio/ 2>/dev/null || echo "/sys/class/gpio not available"
	@echo ""
	@echo "raspi-gpio availability:"
	@if command -v raspi-gpio >/dev/null 2>&1; then \
		echo "raspi-gpio is available"; \
		echo "Current GPIO $(GPIO_PIN) state:"; \
		raspi-gpio get $(GPIO_PIN) || echo "Failed to get GPIO state"; \
	else \
		echo "raspi-gpio not found. Install with: sudo apt install raspi-gpio"; \
	fi
	@echo ""
	@echo "Current user: $(whoami)"
	@echo "Running with sudo: $(if [ $(id -u) -eq 0 ]; then echo 'Yes'; else echo 'No - try: sudo make diagnose'; fi)"

# Cleanup GPIO resources
cleanup-gpio:
	@echo "--- Cleaning up GPIO resources ---"
	@if [ -d "$(GPIO_PIN_PATH)" ]; then \
		echo "Setting GPIO $(GPIO_PIN) to LOW before cleanup..."; \
		echo "0" > $(GPIO_VALUE) 2>/dev/null || true; \
		sleep 0.1; \
		echo "Unexporting GPIO $(GPIO_PIN)..."; \
		echo $(GPIO_PIN) > $(GPIO_UNEXPORT); \
	else \
		echo "GPIO $(GPIO_PIN) already cleaned up"; \
	fi
	@echo "--- GPIO cleanup complete ---"

# Legacy aliases for compatibility
reset-devices: cycle-power
shutdown-all: shutdown
startup-all: startup

# Convenience targets for different GPIO pins
gpio11:
	@$(MAKE) $(TARGET) GPIO_PIN=17

gpio13:
	@$(MAKE) $(TARGET) GPIO_PIN=27

gpio15:
	@$(MAKE) $(TARGET) GPIO_PIN=22

gpio16:
	@$(MAKE) $(TARGET) GPIO_PIN=23

gpio18:
	@$(MAKE) $(TARGET) GPIO_PIN=24

# Help for GPIO pin mapping
pin-map:
	@echo "--- Raspberry Pi GPIO Pin Mapping ---"
	@echo "Physical Pin -> GPIO Number"
	@echo "Pin 11 -> GPIO 17 (default)"
	@echo "Pin 13 -> GPIO 27"
	@echo "Pin 15 -> GPIO 22"
	@echo "Pin 16 -> GPIO 23"
	@echo "Pin 18 -> GPIO 24"
	@echo ""
	@echo "Usage examples:"
	@echo "  make startup GPIO_PIN=27  # Use GPIO 27 (Pin 13)"
	@echo "  make gpio13 TARGET=startup # Same as above"

# Emergency: Force GPIO cleanup and reset
emergency-reset:
	@echo "--- Emergency GPIO Reset ---"
	@echo "Forcing GPIO $(GPIO_PIN) cleanup..."
	@echo "0" > $(GPIO_VALUE) 2>/dev/null || true
	@echo $(GPIO_PIN) > $(GPIO_UNEXPORT) 2>/dev/null || true
	@sleep 0.5
	@$(MAKE) setup-gpio
	@echo "--- Emergency reset complete ---"

# Install systemd service
install-service:
	@echo "--- Installing USB Power Cycle and Image Transfer Service ---"
	@echo "Creating systemd service file..."
	@echo "[Unit]" > /tmp/usb-power-cycle.service
	@echo "Description=USB Power Cycle and Image Transfer Service" >> /tmp/usb-power-cycle.service
	@echo "After=multi-user.target" >> /tmp/usb-power-cycle.service
	@echo "Wants=multi-user.target" >> /tmp/usb-power-cycle.service
	@echo "" >> /tmp/usb-power-cycle.service
	@echo "[Service]" >> /tmp/usb-power-cycle.service
	@echo "Type=simple" >> /tmp/usb-power-cycle.service
	@echo "ExecStart=/usr/bin/python3 /home/pi/Documents/usb_power_cycle.py" >> /tmp/usb-power-cycle.service
	@echo "Restart=always" >> /tmp/usb-power-cycle.service
	@echo "RestartSec=10" >> /tmp/usb-power-cycle.service
	@echo "StandardOutput=journal" >> /tmp/usb-power-cycle.service
	@echo "StandardError=journal" >> /tmp/usb-power-cycle.service
	@echo "User=root" >> /tmp/usb-power-cycle.service
	@echo "# Ensure the service has necessary permissions" >> /tmp/usb-power-cycle.service
	@echo "PrivilegeEscalation=yes" >> /tmp/usb-power-cycle.service
	@echo "NoNewPrivileges=no" >> /tmp/usb-power-cycle.service
	@echo "# Environment" >> /tmp/usb-power-cycle.service
	@echo "Environment=\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"" >> /tmp/usb-power-cycle.service
	@echo "# Working Directory" >> /tmp/usb-power-cycle.service
	@echo "WorkingDirectory=/home/pi/Documents" >> /tmp/usb-power-cycle.service
	@echo "" >> /tmp/usb-power-cycle.service
	@echo "[Install]" >> /tmp/usb-power-cycle.service
	@echo "WantedBy=multi-user.target" >> /tmp/usb-power-cycle.service
	@sudo cp /tmp/usb-power-cycle.service /etc/systemd/system/
	@sudo systemctl daemon-reload
	@sudo systemctl enable usb-power-cycle.service
	@echo "Service installed. Commands:"
	@echo "  sudo systemctl start usb-power-cycle    # Start service"
	@echo "  sudo systemctl status usb-power-cycle   # Check status"
	@echo "  sudo journalctl -u usb-power-cycle -f   # View logs"

# Remove systemd service
remove-service:
	@echo "--- Removing USB Power Cycle service ---"
	@sudo systemctl stop usb-power-cycle.service 2>/dev/null || true
	@sudo systemctl disable usb-power-cycle.service 2>/dev/null || true
	@sudo rm -f /etc/systemd/system/usb-power-cycle.service
	@sudo systemctl daemon-reload
	@echo "--- Service removed ---"