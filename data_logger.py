# File: data_logger.py
# A simple script to listen for FSR data broadcast over the network
# and print it to the console. Run this in its own terminal.

import socket

# --- NETWORK CONFIGURATION (must match the main script) ---
UDP_IP = "127.0.0.1"  # This means it will listen on the local machine
UDP_PORT = 5005       # An arbitrary port number

# --- Create a UDP socket ---
# AF_INET for IPv4, SOCK_DGRAM for UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the address and port to listen for data
sock.bind((UDP_IP, UDP_PORT))

print(f"--- FSR Data Logger ---")
print(f"Logger listening for data on {UDP_IP}:{UDP_PORT}")
print("Press Ctrl+C to stop.")

try:
    # --- Main Listening Loop ---
    while True:
        # Wait here until a data packet is received.
        # 1024 is the buffer size (how much data to read at once).
        data, addr = sock.recvfrom(1024) 
        
        # Decode the received bytes into a string and print it
        print("_________________________________________")
        print(data.decode('utf-8'))

except KeyboardInterrupt:
    print("\nLogger stopped by user.")
finally:
    # Cleanly close the socket when the script is stopped
    sock.close()
    print("Socket closed.")

