#!/usr/bin/env python3
"""
Monitor port statistics in real-time to see if they're updating
"""

import requests
import json
import time

FLOODLIGHT_CONTROLLER_URL = "http://localhost:8080"

def monitor_port_stats():
    print("=== Monitoring Port Statistics ===")
    print("Watching h1 (switch 00:00:00:00:00:00:00:01:3) and h2 (switch 00:00:00:00:00:00:00:02:3)")
    print("Press Ctrl+C to stop\n")
    
    # Track previous values
    prev_stats = {}
    
    try:
        while True:
            # Check h1's switch port
            h1_switch = "00:00:00:00:00:00:00:01"
            h1_port = "3"
            
            # Check h2's switch port  
            h2_switch = "00:00:00:00:00:00:00:02"
            h2_port = "3"
            
            for switch_id, port_num, host_name in [(h1_switch, h1_port, "h1"), (h2_switch, h2_port, "h2")]:
                port_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/port/json')
                
                if port_response.status_code == 200:
                    port_data = port_response.json()
                    ports = port_data.get('port_reply', [{}])[0].get('port', [])
                    
                    for port in ports:
                        if str(port.get('port_number')) == port_num:
                            rx_packets = int(port.get('receive_packets', 0))
                            tx_packets = int(port.get('transmit_packets', 0))
                            rx_bytes = int(port.get('receive_bytes', 0))
                            tx_bytes = int(port.get('transmit_bytes', 0))
                            
                            total_packets = rx_packets + tx_packets
                            total_bytes = rx_bytes + tx_bytes
                            
                            key = f"{switch_id}:{port_num}"
                            
                            if key in prev_stats:
                                packet_delta = total_packets - prev_stats[key]['packets']
                                byte_delta = total_bytes - prev_stats[key]['bytes']
                                
                                if packet_delta > 0 or byte_delta > 0:
                                    print(f"{host_name}: +{packet_delta} packets, +{byte_delta} bytes (Total: {total_packets} packets, {total_bytes:,} bytes)")
                                else:
                                    print(f"{host_name}: No change (Total: {total_packets} packets, {total_bytes:,} bytes)")
                            else:
                                print(f"{host_name}: Initial - {total_packets} packets, {total_bytes:,} bytes")
                            
                            prev_stats[key] = {'packets': total_packets, 'bytes': total_bytes}
                            break
                else:
                    print(f"{host_name}: Error getting port stats")
            
            print(f"--- {time.strftime('%H:%M:%S')} ---")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nStopped monitoring")

if __name__ == "__main__":
    monitor_port_stats()
