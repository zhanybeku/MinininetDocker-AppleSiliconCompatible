#!/usr/bin/env python3
"""
HTTP Traffic Generator for Mininet
This script generates HTTP traffic between hosts in the network
"""

import time
import sys
import subprocess
import threading
from datetime import datetime

def generate_http_requests(server_ip, server_port=8080, interval=2, duration=60):
    """Generate HTTP requests to a server"""
    print(f"Starting HTTP client - sending requests to {server_ip}:{server_port}")
    start_time = time.time()
    request_count = 0
    
    while (time.time() - start_time) < duration:
        try:
            # Use curl to make HTTP request
            result = subprocess.run([
                'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                f'http://{server_ip}:{server_port}'
            ], capture_output=True, text=True, timeout=5)
            
            request_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if result.returncode == 0:
                print(f"[{timestamp}] Request #{request_count}: HTTP {result.stdout}")
            else:
                print(f"[{timestamp}] Request #{request_count}: Failed")
                
        except subprocess.TimeoutExpired:
            print(f"[{timestamp}] Request #{request_count}: Timeout")
        except Exception as e:
            print(f"[{timestamp}] Request #{request_count}: Error - {e}")
            
        time.sleep(interval)
    
    print(f"HTTP client finished. Sent {request_count} requests in {duration} seconds")

def start_http_server(port=8080):
    """Start a simple HTTP server"""
    print(f"Starting HTTP server on port {port}")
    try:
        subprocess.run(['python3', '-m', 'http.server', str(port)])
    except KeyboardInterrupt:
        print("HTTP server stopped")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Server mode: python3 generate_http_traffic.py server [port]")
        print("  Client mode: python3 generate_http_traffic.py client <server_ip> [port] [interval] [duration]")
        print("")
        print("Examples:")
        print("  python3 generate_http_traffic.py server 8080")
        print("  python3 generate_http_traffic.py client 10.0.0.1 8080 1 30")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        start_http_server(port)
    
    elif mode == "client":
        if len(sys.argv) < 3:
            print("Error: Client mode requires server IP")
            sys.exit(1)
            
        server_ip = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 8080
        interval = float(sys.argv[4]) if len(sys.argv) > 4 else 2
        duration = int(sys.argv[5]) if len(sys.argv) > 5 else 60
        
        generate_http_requests(server_ip, port, interval, duration)
    
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
