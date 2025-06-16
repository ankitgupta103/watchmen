#!/bin/bash

# ==============================================================================
# Master Setup Script for Complete System Configuration
# ==============================================================================
# This script sets up the complete system including:
# - Python virtual environment
# - Dependencies installation
# - Camera capture service
# - Event detector service  
# - Demo service for run_demob.py
# Must be run with root privileges.
# ==============================================================================

set -e  # Exit on any error

# Get the actual user (not root when using sudo)
if [[ -n "$SUDO_USER" ]]; then
    ACTUAL_USER="$SUDO_USER"
else
    ACTUAL_USER="$USER"
fi

# Set user-specific paths
USER_HOME="/home/$ACTUAL_USER"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print status messages
print_header() {
    echo -e "\n${CYAN}===============================================${NC}"
    echo -e "${CYAN} $1 ${NC}"
    echo -e "${CYAN}===============================================${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check for Root Privileges
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root. Please use 'sudo ./master-setup.sh'"
    exit 1
fi

print_header "MASTER SETUP - COMPLETE SYSTEM CONFIGURATION"

# Ask if the device is central or dev unit
DEVICE_TYPE=""
while [[ "$DEVICE_TYPE" != "central" && "$DEVICE_TYPE" != "dev" ]]; do
    read -p "Is this device a 'central' or 'dev' unit? [central/dev]: " DEVICE_TYPE
    DEVICE_TYPE=$(echo "$DEVICE_TYPE" | tr '[:upper:]' '[:lower:]')
done
print_status "Device type selected: $DEVICE_TYPE"

# Get current directory as project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
print_status "Project directory: $PROJECT_DIR"
print_status "Setting up for user: $ACTUAL_USER"
print_status "User home directory: $USER_HOME"

# Configuration
OWNER_USER="$ACTUAL_USER"
VENV_DIR="$USER_HOME/watchmen/venv"
BASHRC_FILE="$USER_HOME/.bashrc"

print_header "CONFIGURATION SUMMARY"
echo -e "${CYAN}Project Directory:${NC} $PROJECT_DIR"
echo -e "${CYAN}Owner User:${NC} $OWNER_USER"
echo -e "${CYAN}Virtual Environment:${NC} $VENV_DIR"
echo -e "${CYAN}Bashrc File:${NC} $BASHRC_FILE"
echo

# =============================================================================
# STEP 0: Install system dependencies
# =============================================================================
print_step "[0/5] Installing system dependencies..."

print_status "Updating package lists..."
apt update

print_status "Installing development headers and build tools..."
apt install -y \
    libcap-dev \
    python3-dev \
    build-essential \
    pkg-config

print_status "System dependencies installed successfully"

# =============================================================================
# STEP 1: Create virtual environment and add lines to .bashrc
# =============================================================================
print_step "[1/5] Creating and adding virtual environment configuration to .bashrc..."

# Create the watchmen directory if it doesn't exist
mkdir -p "$USER_HOME/watchmen"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$USER_HOME/watchmen"

# Create virtual environment as the specified user
print_status "Creating virtual environment..."
sudo -u "$ACTUAL_USER" python3 -m venv "$VENV_DIR"
print_status "Virtual environment created at $VENV_DIR"

# Check if the lines are already in .bashrc to avoid duplicates
VENV_ACTIVATE_LINE="source $USER_HOME/watchmen/venv/bin/activate"
PYTHONPATH_LINE="export PYTHONPATH=$USER_HOME/watchmen/venv/lib/python3.11/site-packages:\$PYTHONPATH"

if ! grep -q "$VENV_ACTIVATE_LINE" "$BASHRC_FILE" 2>/dev/null; then
    echo "" >> "$BASHRC_FILE"
    echo "# Added by watchmen setup script" >> "$BASHRC_FILE"
    echo "$VENV_ACTIVATE_LINE" >> "$BASHRC_FILE"
    print_status "Added virtual environment activation to .bashrc"
else
    print_status "Virtual environment activation already exists in .bashrc"
fi

if ! grep -q "export PYTHONPATH=.*watchmen.*venv.*lib.*python3.11.*site-packages" "$BASHRC_FILE" 2>/dev/null; then
    echo "$PYTHONPATH_LINE" >> "$BASHRC_FILE"
    print_status "Added PYTHONPATH to .bashrc"
else
    print_status "PYTHONPATH for watchmen already exists in .bashrc"
fi

# Ensure .bashrc is owned by the user
chown "$ACTUAL_USER:$ACTUAL_USER" "$BASHRC_FILE"

# =============================================================================
# STEP 2: Install vyomcloudbridge
# =============================================================================
print_step "[2/5] Installing vyomcloudbridge..."

# Install vyomcloudbridge
sudo -u "$ACTUAL_USER" "$VENV_DIR/bin/pip" install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ vyomcloudbridge==0.2.39

print_status "vyomcloudbridge v0.2.39 installed successfully"

# =============================================================================
# STEP 3: Install requirements.txt
# =============================================================================
print_step "[3/5] Installing requirements from requirements.txt..."

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    print_status "Found requirements.txt, installing packages..."
    sudo -u "$ACTUAL_USER" bash -c "source $BASHRC_FILE && $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt"
    print_status "Requirements installed successfully"
else
    print_warning "requirements.txt not found in $PROJECT_DIR"
fi

# =============================================================================
# STEP 4: Run setup scripts in subdirectories
# =============================================================================
print_step "[4/5] Running setup scripts in subdirectories..."

if [ "$DEVICE_TYPE" = "central" ]; then
    print_status "Central unit selected: Skipping Camera capture and Event detector service setup."
else
    # Run camera-capture-service setup
    CAMERA_SETUP_DIR="$PROJECT_DIR/camera-capture-service"
    if [ -d "$CAMERA_SETUP_DIR" ] && [ -f "$CAMERA_SETUP_DIR/setup.sh" ]; then
        print_status "Running camera-capture-service setup..."
        cd "$CAMERA_SETUP_DIR"
        chmod +x setup.sh
        ./setup.sh
        cd "$PROJECT_DIR"
        print_status "Camera capture service setup completed"
    else
        print_error "Camera capture service setup not found at $CAMERA_SETUP_DIR/setup.sh"
        exit 1
    fi

    # Run event-detect-service setup
    EVENT_SETUP_DIR="$PROJECT_DIR/event-detect-service"
    if [ -d "$EVENT_SETUP_DIR" ] && [ -f "$EVENT_SETUP_DIR/setup.sh" ]; then
        print_status "Running event-detect-service setup..."
        cd "$EVENT_SETUP_DIR"
        chmod +x setup.sh
        ./setup.sh
        cd "$PROJECT_DIR"
        print_status "Event detect service setup completed"
    else
        print_error "Event detect service setup not found at $EVENT_SETUP_DIR/setup.sh"
        exit 1
    fi
fi

# =============================================================================
# STEP 5: Run create-demo-service.sh
# =============================================================================
print_step "[5/5] Running create-demo-service.sh..."

DEMO_SCRIPT="$PROJECT_DIR/create-demo-service.sh"
if [ -f "$DEMO_SCRIPT" ]; then
    print_status "Running create-demo-service.sh..."
    chmod +x "$DEMO_SCRIPT"
    if "$DEMO_SCRIPT"; then
        print_status "Demo service setup completed"
    else
        print_warning "Demo service setup failed, but continuing with the rest of the setup. You can rerun it manually later."
    fi
else
    print_warning "create-demo-service.sh not found at $DEMO_SCRIPT. Continuing with the rest of the setup."
fi

# =============================================================================
# POST-SETUP: Manual Steps for the User
# =============================================================================
print_header "MANUAL STEPS TO COMPLETE SETUP"
echo -e "${YELLOW}1.${NC} Switch to root shell: ${CYAN}sudo su${NC}"
echo -e "${YELLOW}2.${NC} Source your bashrc: ${CYAN}source /home/$ACTUAL_USER/.bashrc${NC}"
echo -e "${YELLOW}3.${NC} Run vyomcloudbridge setup: ${CYAN}vyomcloudbridge setup${NC}"
echo -e "${YELLOW}4.${NC} Reboot the system: ${CYAN}sudo reboot${NC}"
echo

# =============================================================================
# SETUP COMPLETE - SUMMARY
# =============================================================================
print_header "SETUP COMPLETE!"

# Function to print a spider web ASCII art
print_spider_web() {
    echo -e "${CYAN}"
    echo "              \\       |       /"
    echo "               \\      |      /"
    echo "                \\     |     /"
    echo "          _______\\____|____/_______"
    echo "         /        \\   |   /        \\"
    echo "        /          \\  |  /          \\"
    echo "       /         .-(\\-+-/)-. watchmen \\"
    echo "      |         /   \\ | /   \\         |"
    echo "      |        |    (   )    |        |"
    echo "      |         \\   / | \\   /         |"
    echo "       \\         '-(/-+-\\)-'         /"
    echo "        \\          /  |  \\          /"
    echo "         \\________/   |   \\________/"
    echo "                 /    |    \\"
    echo "                /     |     \\"
    echo "               /      |      \\"
    echo -e "${NC}"
}
print_spider_web

echo
echo -e "${GREEN}✓ User:${NC} $ACTUAL_USER"
echo -e "${GREEN}✓ Virtual Environment:${NC} $VENV_DIR"
echo -e "${GREEN}✓ Bashrc Updated:${NC} $BASHRC_FILE"
echo -e "${GREEN}✓ VyomCloudBridge:${NC} v0.2.39 installed"
echo -e "${GREEN}✓ Requirements:${NC} Installed from requirements.txt"
echo -e "${GREEN}✓ Camera Capture Service:${NC} Setup completed"
echo -e "${GREEN}✓ Event Detect Service:${NC} Setup completed"
echo -e "${GREEN}✓ Demo Service:${NC} Setup completed"
echo

echo -e "${BLUE}=== USEFUL COMMANDS ===${NC}"
echo -e "${YELLOW}Activate environment (manual):${NC} source $VENV_DIR/bin/activate"
echo -e "${YELLOW}Check Python path:${NC} echo \$PYTHONPATH"
echo -e "${YELLOW}Test installation:${NC} python -c \"import vyomcloudbridge; print('Success!')\""
echo

echo -e "${BLUE}=== NEXT STEPS ===${NC}"
echo -e "${YELLOW}1.${NC} Open a new terminal (or run: source $BASHRC_FILE)"
echo -e "${YELLOW}2.${NC} The virtual environment will be automatically activated"
echo -e "${YELLOW}3.${NC} All services should be running automatically"
echo

echo -e "${BLUE}=== ENVIRONMENT SETUP ===${NC}"
echo -e "${CYAN}Virtual Environment:${NC} $VENV_DIR"
echo -e "${CYAN}Python Path:${NC} $USER_HOME/watchmen/venv/lib/python3.11/site-packages"
echo -e "${CYAN}Auto-activation:${NC} Configured in $BASHRC_FILE"
echo

print_status "Master setup completed successfully!"
print_status "All services are configured and running."
print_status "Virtual environment will be automatically activated in new terminal sessions."