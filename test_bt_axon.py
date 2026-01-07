#!/usr/bin/env python3
"""
Simulate Bittensor axon behavior
Tests external accessibility for validators
"""
import socket
import json
from datetime import datetime

HOST = '0.0.0.0'
PORT = 8091

def handle_connection(conn, addr):
    """Handle connection like a Bittensor axon"""
    try:
        # Receive data
        data = conn.recv(4096)
        
        if data:
            print(f"  📦 Received {len(data)} bytes")
            try:
                decoded = data.decode('utf-8')
                print(f"  📝 Data preview: {decoded[:200]}")
            except:
                print(f"  📝 Binary data")
        
        # Send Bittensor-like response
        response = {
            "status": "success",
            "axon_port": PORT,
            "timestamp": datetime.now().isoformat(),
            "message": "Axon is accessible"
        }
        
        http_response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "\r\n" +
            json.dumps(response)
        ).encode()
        
        conn.send(http_response)
        print(f"  ✅ Response sent")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    finally:
        conn.close()

print("="*70)
print("  BITTENSOR AXON SIMULATOR")
print("="*70)
print(f"Listening on: {HOST}:{PORT}")
print(f"This simulates how validators will connect to your miner")
print("="*70)
print()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    
    print(f"✅ Axon listening on port {PORT}")
    print(f"⏳ Waiting for validator connections...\n")
    
    conn_num = 0
    while True:
        conn, addr = s.accept()
        conn_num += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"[{timestamp}] 🔵 CONNECTION #{conn_num}")
        print(f"  🌐 From: {addr[0]}:{addr[1]}")
        
        handle_connection(conn, addr)
        print()
