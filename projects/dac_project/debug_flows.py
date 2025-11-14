#!/usr/bin/env python3
"""
Debug script to check what flows and statistics are available
"""

import requests
import json

FLOODLIGHT_CONTROLLER_URL = "http://localhost:8080"

def debug_flows_and_stats():
    print("=== Debugging Flow Detection ===\n")
    
    # Get switches
    switches_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json')
    if switches_response.status_code != 200:
        print("Failed to get switches")
        return
        
    switches = switches_response.json()
    print(f"Found {len(switches)} connected switches\n")
    
    # Check flows on each switch
    total_flows = 0
    for switch in switches:
        switch_id = switch['switchDPID']
        print(f"Switch {switch_id}:")
        
        # Try to get flows
        flow_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/flow/json')
        if flow_response.status_code == 200:
            flow_data = flow_response.json()
            flows = flow_data.get('flows', [])
            print(f"  Flows: {len(flows)}")
            total_flows += len(flows)
            
            # Show first few flows if any
            for i, flow in enumerate(flows[:3]):
                match = flow.get('match', {})
                print(f"    Flow {i+1}: {match}")
                print(f"      Packets: {flow.get('packetCount', 0)}, Bytes: {flow.get('byteCount', 0)}")
        else:
            print(f"  Flows: Error {flow_response.status_code}")
        
        # Get port stats
        port_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/port/json')
        if port_response.status_code == 200:
            port_data = port_response.json()
            ports = port_data.get('port_reply', [{}])[0].get('port', [])
            
            active_ports = 0
            total_packets = 0
            for port in ports:
                if port.get('port_number') != 'local':
                    rx_packets = int(port.get('receive_packets', 0))
                    tx_packets = int(port.get('transmit_packets', 0))
                    if rx_packets > 0 or tx_packets > 0:
                        active_ports += 1
                        total_packets += rx_packets + tx_packets
            
            print(f"  Port stats: {active_ports} active ports, {total_packets} total packets")
        else:
            print(f"  Port stats: Error {port_response.status_code}")
        
        print()
    
    print(f"Total flows across all switches: {total_flows}")
    
    # Check devices
    devices_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/device/')
    if devices_response.status_code == 200:
        devices_data = devices_response.json()
        devices = devices_data.get('devices', [])
        
        print(f"\nFound {len(devices)} devices:")
        for device in devices:
            ipv4_addresses = device.get('ipv4', [])
            if ipv4_addresses:
                for ip in ipv4_addresses:
                    if ip and ip != '0.0.0.0':
                        attachment_points = device.get('attachmentPoint', [])
                        print(f"  {ip}: {len(attachment_points)} attachment points")
                        for ap in attachment_points:
                            print(f"    -> {ap.get('switch', 'unknown')}:{ap.get('port', 'unknown')}")

if __name__ == "__main__":
    try:
        debug_flows_and_stats()
    except Exception as e:
        print(f"Error: {e}")
