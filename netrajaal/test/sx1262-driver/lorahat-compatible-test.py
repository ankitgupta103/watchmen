# LoRaHat compatible test for OpenMV + Core1262
import time

def test_lorahat_communication():
    """Test communication with LoRaHat using matching parameters"""
    
    print("=== LoRaHat Compatible Communication Test ===")
    print("Configuration:")
    print("- Frequency: 868 MHz")
    print("- Spreading Factor: SF9 (for ~2400 bps)")
    print("- Bandwidth: 125 kHz") 
    print("- Power: 22 dBm")
    print("- Preamble: 12 symbols")
    print("- CRC: Enabled")
    
    try:
        # Initialize with TCXO
        lora = SX1262()
        print("\n✓ LoRa module initialized successfully!")
        
        # Test transmission
        print("\n--- Testing Transmission ---")
        test_messages = [
            "Hello LoRaHat!",
            "OpenMV Core1262 Test",
            "SF9 BW125 868MHz",
            "Message 4",
            "Final test message"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\nSending message {i}/5: {message}")
            
            if lora.send_data(message):
                print(f"✓ Message {i} sent successfully!")
            else:
                print(f"✗ Message {i} failed to send")
            
            # Wait between messages
            time.sleep(2)
        
        # Test reception
        print("\n--- Testing Reception ---")
        print("Listening for 30 seconds...")
        print("Please send a message from your LoRaHat now...")
        
        for attempt in range(3):  # 3 attempts of 30 seconds each
            print(f"\nListening attempt {attempt + 1}/3...")
            received = lora.receive_data(timeout_ms=30000)
            
            if received:
                try:
                    message = received.decode('utf-8', errors='ignore')
                    print(f"✓ RECEIVED MESSAGE: '{message}'")
                    print(f"  Raw bytes: {received}")
                    break
                except:
                    print(f"✓ RECEIVED DATA: {received}")
                    break
            else:
                print("  No message received in this attempt")
        else:
            print("\n✗ No messages received from LoRaHat")
            print("Possible issues:")
            print("- LoRaHat not transmitting")
            print("- Different LoRa parameters")
            print("- RF interference")
        
        print("\n--- Bidirectional Test ---")
        print("Testing both send and receive...")
        
        for round_num in range(3):
            print(f"\nRound {round_num + 1}/3:")
            
            # Send
            msg = f"OpenMV Round {round_num + 1}"
            print(f"  Sending: {msg}")
            if lora.send_data(msg):
                print("  ✓ Sent")
            else:
                print("  ✗ Send failed")
            
            # Listen for response
            print("  Listening for response...")
            received = lora.receive_data(timeout_ms=10000)
            if received:
                try:
                    response = received.decode('utf-8', errors='ignore')
                    print(f"  ✓ Response: '{response}'")
                except:
                    print(f"  ✓ Response: {received}")
            else:
                print("  - No response")
            
            time.sleep(3)
        
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

def simple_send_test():
    """Simple send test - just transmit"""
    try:
        lora = SX1262()
        
        counter = 0
        while True:
            message = f"OpenMV-{counter:03d}: Hello LoRaHat!"
            print(f"Sending: {message}")
            
            if lora.send_data(message):
                print("✓ Sent successfully!")
            else:
                print("✗ Send failed")
            
            counter += 1
            time.sleep(5)  # Send every 5 seconds
            
    except KeyboardInterrupt:
        print("\nTest stopped")
    except Exception as e:
        print(f"Error: {e}")

def simple_receive_test():
    """Simple receive test - just listen"""
    try:
        lora = SX1262()
        print("Listening for LoRaHat messages...")
        print("Press Ctrl+C to stop")
        
        while True:
            received = lora.receive_data(timeout_ms=60000)  # 1 minute timeout
            
            if received:
                try:
                    message = received.decode('utf-8', errors='ignore')
                    print(f"✓ RECEIVED: '{message}'")
                except:
                    print(f"✓ RECEIVED: {received}")
            else:
                print("- Timeout, still listening...")
                
    except KeyboardInterrupt:
        print("\nStopped listening")
    except Exception as e:
        print(f"Error: {e}")

# Choose which test to run:
if __name__ == "__main__":
    # Uncomment the test you want to run:
    test_lorahat_communication()    # Full bidirectional test
    # simple_send_test()            # Just send messages
    # simple_receive_test()         # Just listen for messages