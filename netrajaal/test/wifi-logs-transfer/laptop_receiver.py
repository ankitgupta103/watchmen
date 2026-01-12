import socket
import sys
from datetime import datetime

HOST = "0.0.0.0"  
PORT = 5000  

def get_local_ip():
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

def start_server():
    """Start TCP server to receive data from OpenMV"""
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Bind to host and port
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        
        local_ip = get_local_ip()
        print("=" * 60)
        print("OpenMV Data Receiver Server")
        print("=" * 60)
        print(f"Listening on {local_ip}:{PORT}")
        print(f"Make sure your OpenMV script uses IP: {local_ip}")
        print("Waiting for OpenMV connection...")
        print("=" * 60)
        
        while True:
            # Accept connection
            client_socket, client_address = server_socket.accept()
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
            print(f"Connected from: {client_address[0]}:{client_address[1]}")
            
            try:
                while True:
                    # Receive data
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    # Decode and display
                    message = data.decode('utf-8', errors='ignore')
                    print(f"Received: {message.strip()}")
                    
                    # Send acknowledgment
                    client_socket.sendall(b"ACK\n")
                    
            except socket.error as e:
                print(f"Socket error: {e}")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                client_socket.close()
                print(f"Connection closed from {client_address[0]}")
                
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()
        print("Server socket closed")

if __name__ == "__main__":
    start_server()
