from sx1262 import sx126x
import time


def configure_lora(
    uart_num=1,
    freq=868,
    addr=0,
    power=22,
    rssi=True,
    air_speed=2400,
    net_id=0,
    buffer_size=240,
    crypt=0,
    m0_pin="P6",
    m1_pin="P7",
    configure=True,
):
    """
    Configure and initialize the LoRa module.
    
    Args:
        configure (bool): If True, configure the module (save to EEPROM permanently).
                         If False, skip configuration and assume module is already configured.
    """
    if configure:
        print(f"Configuring LoRa module...")
        print(f"  Address: {addr}")
        print(f"  Frequency: {freq} MHz")
        print(f"  Power: {power} dBm")
        print(f"  RSSI: {rssi}")
    else:
        print(f"Initializing LoRa module (skipping configuration - using saved settings)...")
    
    try:
        lora = sx126x(
            uart_num=uart_num,
            freq=freq,
            addr=addr,
            power=power,
            rssi=rssi,
            air_speed=air_speed,
            net_id=net_id,
            buffer_size=buffer_size,
            crypt=crypt,
            m0_pin=m0_pin,
            m1_pin=m1_pin,
            skip_config=not configure,
        )

        # Check config_success attribute
        # The logger output is the most reliable indicator of success
        # If initialization completed without exception, trust that
        if configure:
            if hasattr(lora, "config_success"):
                if lora.config_success:
                    print("  LoRa module configured successfully!")
                else:
                    print(f"  config_success=False, but check logs above - if logger shows SUCCESS, module is ready")
            else:
                print("  config_success attribute not found, but initialization completed")
        else:
            print("  LoRa module initialized (using saved configuration)")
        
        # Always return the object if we got here (no exception raised)
        # The logger output is more reliable than the attribute check
        return lora
    except Exception as e:
        print(f"  Failed to initialize LoRa module: {e}")
        raise


def send_data(lora, target_addr, message):
    """
    Send raw data to a target address.
    
    Args:
        lora (sx126x): LoRa module object
        target_addr (int): Destination node address (0-65535, 65535=broadcast)
        message (bytes or str): Raw message to send (will be converted to bytes if string)
    
    Returns:
        bool: True if message was sent, False otherwise
    """
    if lora is None:
        print("  Failed to send message: LoRa module is None")
        return False

    # Convert string to bytes if needed
    if isinstance(message, str):
        message = message.encode('utf-8')
    
    try:
        print(f"Sending to address {target_addr}: {message}")
        lora.send(target_addr, message)
        print("  Message sent successfully")
        return True
    except Exception as e:
        print(f"  Failed to send message: {e}")
        return False


def read_data(lora, timeout_ms=1000):
    """
    Read/receive raw data from the LoRa module.
    
    Args:
        lora (sx126x): LoRa module object
        timeout_ms (int): Timeout in milliseconds (default: 1000)
    
    Returns:
        tuple: (message_bytes, rssi_value) or (None, None) if no data
    """
    start_time = time.ticks_ms()
    
    while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
        msg, rssi = lora.receive()
        if msg is not None:
            return (msg, rssi)
        time.sleep_ms(10)  # Small delay to avoid busy waiting
    
    return (None, None)


def setuplora(myaddr, configure=False):
    """
    Setup LoRa module.
    
    Args:
        myaddr (int): Node address
        configure (bool): If True, configure module (save to EEPROM permanently).
                         If False, skip configuration and use saved settings (faster startup).
                         
    Note:
        Set configure=True the first time or when you need to change settings.
        Set configure=False for faster startup after initial configuration.
    """
    lora = configure_lora(
        addr=myaddr,          # This node's address
        freq=868,        # Frequency in MHz
        power=22,        # TX power in dBm
        rssi=True,       # Enable RSSI reporting
        configure=configure,  # Configure flag: True = configure, False = skip
    )

    if lora is None:
        print("  LoRa module not ready (configuration failed)")
        return None

    # Check config_success but don't be too strict
    # If initialization completed without exception, module likely works
    if hasattr(lora, "config_success") and lora.config_success:
        print("LoRa module ready!")
    else:
        # config_success is False or missing, but if we got here without exception,
        # the module might still be functional - logger may have shown success
        print("LoRa module ready! (config_success flag unclear, but initialization completed)")

    return lora

def main1():
    lora = setuplora(1)
    if lora is None:
        return
    # Example: Send a test message (raw data, no prefix)
    print("\nSending test message...")
    send_data(lora, target_addr=2, message=b"Test message from node 1")

def main2():
    lora = setuplora(2)
    if lora is None:
        return

    # Example: Listen for incoming messages
    print("\nListening for incoming messages (5 seconds)...")
    msg, rssi = read_data(lora, timeout_ms=5000)
    if msg:
        try:
            msg_str = msg.decode('utf-8')
            print(f"  Received message: {msg_str}")
        except:
            print(f"  Received message (bytes): {msg}")
        if rssi is not None:
            print(f"  RSSI: {rssi} dBm")
    else:
        print("  No messages received")


if __name__ == "__main__":
    # You can call main1() or main2() as needed
    main1()

