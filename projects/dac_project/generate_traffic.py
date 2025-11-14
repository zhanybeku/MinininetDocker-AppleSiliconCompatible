#!/usr/bin/env python3
"""
Script to generate high traffic for testing suspicious activity detection.
This will help trigger traffic threshold alerts.

Usage:
    python3 generate_traffic.py <target_ip> [duration_seconds]
    
Example:
    python3 generate_traffic.py 10.0.0.2 60
"""

import sys
import socket
import time
import threading

def send_udp_packets(target_ip, target_port, duration, packet_size=1024):
    """Send UDP packets to generate traffic."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = b'X' * packet_size
    
    end_time = time.time() + duration
    packet_count = 0
    
    print(f"[Traffic Generator] Sending UDP packets to {target_ip}:{target_port}")
    print(f"[Traffic Generator] Duration: {duration} seconds, Packet size: {packet_size} bytes")
    
    try:
        while time.time() < end_time:
            try:
                sock.sendto(data, (target_ip, target_port))
                packet_count += 1
                if packet_count % 1000 == 0:
                    print(f"[Traffic Generator] Sent {packet_count} packets...")
            except Exception as e:
                print(f"[Traffic Generator] Error: {e}")
                break
    finally:
        sock.close()
        print(f"[Traffic Generator] Finished. Total packets sent: {packet_count}")
        print(f"[Traffic Generator] Estimated bytes: {packet_count * packet_size:,}")

def send_tcp_syn(target_ip, target_port, duration):
    """Send TCP SYN packets (connection attempts) to generate traffic."""
    end_time = time.time() + duration
    packet_count = 0
    
    print(f"[Traffic Generator] Sending TCP SYN packets to {target_ip}:{target_port}")
    print(f"[Traffic Generator] Duration: {duration} seconds")
    
    while time.time() < end_time:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            sock.connect_ex((target_ip, target_port))
            sock.close()
            packet_count += 1
            if packet_count % 100 == 0:
                print(f"[Traffic Generator] Sent {packet_count} connection attempts...")
        except Exception as e:
            pass  # Expected to fail for most ports
        time.sleep(0.01)  # Small delay to avoid overwhelming
    
    print(f"[Traffic Generator] Finished. Total connection attempts: {packet_count}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_traffic.py <target_ip> [duration_seconds] [mode]")
        print("  target_ip: IP address to send traffic to (e.g., 10.0.0.2)")
        print("  duration_seconds: How long to generate traffic (default: 60)")
        print("  mode: 'udp' or 'tcp' (default: 'udp')")
        print("\nExample:")
        print("  python3 generate_traffic.py 10.0.0.2 60")
        print("  python3 generate_traffic.py 10.0.0.2 60 tcp")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    mode = sys.argv[3].lower() if len(sys.argv) > 3 else 'udp'
    
    print("="*70)
    print("TRAFFIC GENERATOR - Suspicious Activity Simulation")
    print("="*70)
    print(f"Target: {target_ip}")
    print(f"Duration: {duration} seconds")
    print(f"Mode: {mode.upper()}")
    print("="*70)
    print("\nThis will generate high traffic to trigger threshold alerts.")
    print("Press Ctrl+C to stop early.\n")
    
    try:
        if mode == 'udp':
            # Use a high port number for UDP
            send_udp_packets(target_ip, 9999, duration)
        elif mode == 'tcp':
            # Try multiple ports to generate more traffic
            threads = []
            for port in [80, 443, 22, 21, 3389]:
                t = threading.Thread(target=send_tcp_syn, args=(target_ip, port, duration))
                t.daemon = True
                t.start()
                threads.append(t)
            
            # Wait for all threads
            for t in threads:
                t.join()
        else:
            print(f"Unknown mode: {mode}. Use 'udp' or 'tcp'")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[Traffic Generator] Interrupted by user")
    except Exception as e:
        print(f"\n[Traffic Generator] Error: {e}")

if __name__ == "__main__":
    main()

