#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#
# OpenMV RT1062 LoRa SX126X Communication Script
# Adapted from Raspberry Pi version
#
# This script is for OpenMV RT1062 with SX126X LoRa HAT
# Make sure to connect:
# - UART pins (TX, RX) to your chosen UART port
# - M0 and M1 control pins to specified GPIO pins
# - Power and ground connections
#

import sx126x_openmv as sx126x
import time
from machine import Pin

# Initialize LED for status indication (use a GPIO pin as LED)
# Change 'P2' to whatever pin you have an LED connected to
try:
    led = Pin('P2', Pin.OUT)  # Built-in LED or external LED pin
    led_available = True
except:
    led_available = False
    print("LED pin not available, continuing without LED indication")

# Temperature reading for OpenMV (if available)
def get_cpu_temp():
    try:
        # OpenMV doesn't have easy CPU temp access like RPi
        # You could read from an external temperature sensor if connected
        # For now, return a dummy value
        return 25.0  # Dummy temperature
    except:
        return 25.0

def send_message():
    """Send a custom message via LoRa"""
    print("\n=== Send Message ===")
    print("Enter message in format: address,frequency,message")
    print("Example: 0,868,Hello World")
    print("This will send 'Hello World' to node address 0 at 868MHz")

    # For OpenMV, we'll use a predefined message since we don't have interactive input
    # You can modify this to suit your needs
    get_rec = "0,868,Hello from OpenMV!"
    print(f"Sending: {get_rec}")

    try:
        get_t = get_rec.split(",")

        if len(get_t) < 3:
            print("Invalid format. Need: address,frequency,message")
            return

        target_addr = int(get_t[0])
        target_freq = int(get_t[1])
        message = get_t[2]

        offset_frequency = target_freq - (850 if target_freq > 850 else 410)

        # Create message packet
        # Format: [target_high][target_low][target_freq][own_high][own_low][own_freq][message]
        data = bytes([target_addr >> 8]) + \
               bytes([target_addr & 0xff]) + \
               bytes([offset_frequency]) + \
               bytes([node.addr >> 8]) + \
               bytes([node.addr & 0xff]) + \
               bytes([node.offset_freq]) + \
               message.encode()

        node.send(data)
        print("Message sent successfully!")
        if led_available:
            led.value(1)  # LED on
            time.sleep_ms(200)
            led.value(0)  # LED off

    except Exception as e:
        print(f"Error sending message: {e}")

def send_cpu_temperature():
    """Send CPU temperature periodically"""
    print("Sending CPU temperature...")

    # Broadcast message (address 255.255 = 65535)
    temp = get_cpu_temp()
    message = f"OpenMV Temperature: {temp} C"

    # Broadcast packet format
    data = bytes([255]) + bytes([255]) + bytes([18]) + \
           bytes([255]) + bytes([255]) + bytes([12]) + \
           message.encode()

    node.send(data)
    print(f"Temperature sent: {temp}°C")
    if led_available:
        led.value(1)  # LED on
        time.sleep_ms(100)
        led.value(0)  # LED off

def test_uart_connection():
    """Test basic UART communication"""
    print("\n=== UART Connection Test ===")

    # Test if we can communicate with the module
    print("Testing UART communication...")

    # Set to configuration mode
    node.M0.value(0)  # LOW
    node.M1.value(1)  # HIGH
    time.sleep_ms(200)

    # Clear buffer
    while node.ser.any():
        node.ser.read()

    # Send simple command to read module info
    test_cmd = bytes([0xC1, 0x00, 0x09])
    print(f"Sending test command: {[hex(x) for x in test_cmd]}")
    node.ser.write(test_cmd)
    time.sleep_ms(500)

    if node.ser.any():
        response = node.ser.read()
        print(f"Received response: {[hex(x) for x in response] if response else 'None'}")
        if response and len(response) > 0:
            print("✓ UART communication working")
            return True
        else:
            print("✗ Empty response")
    else:
        print("✗ No response from module")

    print("UART test failed. Check connections:")
    print("- TX/RX might be swapped")
    print("- Wrong UART port selected")
    print("- Module power issues")
    return False

def menu():
    """Display menu options"""
    print("\n=== OpenMV LoRa Menu ===")
    print("1. Send custom message")
    print("2. Send temperature")
    print("3. Check LoRa settings")
    print("4. Test UART connection")
    print("5. Start listening mode")
    print("6. Exit")
    print("Choose option (1-6):")

# Main program
try:
    # Initialize LoRa module
    # Adjust UART number and GPIO pins according to your wiring
    # UART 3 is commonly available, but check your OpenMV documentation
    # Pin names should match your actual connections (e.g., 'P0', 'P1', etc.)

    print("Initializing LoRa SX126X module...")
    node = sx126x.sx126x(
        uart_num=1,        # UART port number - adjust as needed
        freq=868,          # Frequency in MHz
        addr=0,            # Node address
        power=22,          # Transmission power in dBm
        rssi=True,         # Enable RSSI reporting
        air_speed=2400,    # Air data rate
        m0_pin='P6',       # M0 control pin - adjust to your wiring
        m1_pin='P7'        # M1 control pin - adjust to your wiring
    )

    print("LoRa module initialized successfully!")
    print(f"Node address: {node.addr}")
    print(f"Frequency: {node.start_freq + node.offset_freq}.125MHz")
    if led_available:
        led.value(1)  # LED on
        time.sleep_ms(500)
        led.value(0)  # LED off

    # Main loop
    mode = "menu"  # Start in menu mode
    last_temp_send = time.ticks_ms()
    temp_interval = 10000  # Send temperature every 10 seconds

    while True:
        if mode == "menu":
            menu()
            # For demonstration, cycle through functions automatically
            # In a real application, you might use buttons or serial input
            time.sleep_ms(2000)

            # Demo sequence: test UART first, then other functions
            print("Demo: Testing UART connection...")
            if test_uart_connection():
                print("Demo: Sending custom message...")
                send_message()
                time.sleep_ms(3000)

                print("Demo: Sending temperature...")
                send_cpu_temperature()
                time.sleep_ms(3000)

                print("Demo: Entering listening mode for 10 seconds...")
                mode = "listen"
                listen_start = time.ticks_ms()
            else:
                print("UART test failed, skipping other demos")
                time.sleep_ms(5000)  # Wait before retrying

        elif mode == "listen":
            # Listen for incoming messages
            node.receive()

            # Check if we should send temperature
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, last_temp_send) > temp_interval:
                send_cpu_temperature()
                last_temp_send = current_time

            # Return to menu after 10 seconds of listening
            if time.ticks_diff(current_time, listen_start) > 10000:
                mode = "menu"
                print("Returning to menu mode...")

            time.sleep_ms(100)  # Small delay to prevent overwhelming the CPU

        # Optional: Add button handling here
        # if button_pressed():
        #     mode = "menu"

except KeyboardInterrupt:
    print("\nProgram interrupted by user")
except Exception as e:
    print(f"Error: {e}")
    # Blink LED rapidly to indicate error
    if led_available:
        for i in range(10):
            led.value(1)  # LED on
            time.sleep_ms(100)
            led.value(0)  # LED off
            time.sleep_ms(100)

print("Program ended")
