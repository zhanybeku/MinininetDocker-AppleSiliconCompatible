#!/usr/bin/env python3
"""
Simple script to test TCP port connectivity.
Usage: python3 test_port.py <host> <port>
"""
import sys
import socket
import time

def test_port(host, port, timeout=3):
    """Test if a TCP port is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start_time = time.time()
        result = sock.connect_ex((host, port))
        elapsed = time.time() - start_time
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} on {host} is REACHABLE (connection succeeded in {elapsed:.2f}s)")
            return True
        else:
            print(f"❌ Port {port} on {host} is NOT reachable (error code: {result})")
            return False
    except socket.timeout:
        print(f"⏱️  Port {port} on {host} TIMED OUT after {timeout}s (likely blocked by ACL)")
        return False
    except Exception as e:
        print(f"❌ Error testing {host}:{port}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 test_port.py <host> <port>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    test_port(host, port)

