#!/usr/bin/env python3
"""
Test script to generate connection attempts to blocked protocol ports.
This will help test the suspicious activity detection system.

Usage:
    python3 test_blocked_protocols.py <source_ip> <target_ip> [protocol]
    
Examples:
    python3 test_blocked_protocols.py 10.0.0.1 10.0.0.2 SSH
    python3 test_blocked_protocols.py 10.0.0.1 10.0.0.2 FTP
    python3 test_blocked_protocols.py 10.0.0.1 10.0.0.2  # Tests all blocked protocols
"""

import sys
import socket
import time
import json
import os

# Load config to get protocol ports
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()

# Protocol to port mapping
PROTOCOL_PORTS = {
    'SSH': 22,
    'RDP': 3389,
    'FTP': 21,
    'HTTP': 80,
    'HTTPS': 443,
    'Telnet': 23,
    'SMTP': 25,
    'SNMP': 161
}

def test_connection(target_ip, port, protocol_name, num_attempts=10):
    """Attempt to connect to a specific port multiple times."""
    print(f"\n[Test] Attempting {num_attempts} connections to {target_ip}:{port} ({protocol_name})...")
    
    success_count = 0
    refused_count = 0
    timeout_count = 0
    other_error_count = 0
    
    for i in range(num_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # 1 second timeout
            result = sock.connect_ex((target_ip, port))
            sock.close()
            
            if result == 0:
                success_count += 1
                print(f"  Attempt {i+1}: Connection successful")
            else:
                refused_count += 1
                print(f"  Attempt {i+1}: Connection refused (error code: {result})")
                
        except socket.timeout:
            timeout_count += 1
            print(f"  Attempt {i+1}: Connection timeout")
        except Exception as e:
            other_error_count += 1
            print(f"  Attempt {i+1}: Error - {e}")
        
        # Small delay between attempts
        time.sleep(0.1)
    
    print(f"\n[Test] Results for {protocol_name} ({target_ip}:{port}):")
    print(f"  Successful: {success_count}")
    print(f"  Refused: {refused_count}")
    print(f"  Timeout: {timeout_count}")
    print(f"  Other errors: {other_error_count}")
    
    return {
        'success': success_count,
        'refused': refused_count,
        'timeout': timeout_count,
        'other': other_error_count
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_blocked_protocols.py <source_ip> <target_ip> [protocol]")
        print("\nAvailable protocols: SSH, RDP, FTP, HTTP, HTTPS, Telnet, SMTP, SNMP")
        print("\nExamples:")
        print("  python3 test_blocked_protocols.py 10.0.0.1 10.0.0.2 SSH")
        print("  python3 test_blocked_protocols.py 10.0.0.1 10.0.0.2 FTP")
        print("  python3 test_blocked_protocols.py 10.0.0.1 10.0.0.2  # Tests all blocked protocols")
        sys.exit(1)
    
    source_ip = sys.argv[1]  # Not used directly, but good to know
    target_ip = sys.argv[2]
    protocol = sys.argv[3].upper() if len(sys.argv) > 3 else None
    
    print("="*70)
    print("BLOCKED PROTOCOL CONNECTION TEST")
    print("="*70)
    print(f"Source IP: {source_ip}")
    print(f"Target IP: {target_ip}")
    print(f"Note: Run this from the source host (e.g., in Mininet: h1)")
    print("="*70)
    
    # Get blocked protocols for guest role (default)
    guest_blocked = config['roles']['guest']['blocked_protocols']
    print(f"\nBlocked protocols for 'guest' role: {', '.join(guest_blocked)}")
    
    if protocol:
        # Test specific protocol
        if protocol not in PROTOCOL_PORTS:
            print(f"\nError: Unknown protocol '{protocol}'")
            print(f"Available protocols: {', '.join(PROTOCOL_PORTS.keys())}")
            sys.exit(1)
        
        port = PROTOCOL_PORTS[protocol]
        test_connection(target_ip, port, protocol, num_attempts=20)
    else:
        # Test all blocked protocols
        print(f"\nTesting all blocked protocols for guest role...")
        for protocol_name in guest_blocked:
            if protocol_name in PROTOCOL_PORTS:
                port = PROTOCOL_PORTS[protocol_name]
                test_connection(target_ip, port, protocol_name, num_attempts=10)
                time.sleep(0.5)  # Small delay between protocols
    
    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)
    print("\nNote: Check your dac_app.py output for security alerts.")
    print("Even refused connections should trigger alerts if flows are created.")

if __name__ == "__main__":
    main()

