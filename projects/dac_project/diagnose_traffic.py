#!/usr/bin/env python3
"""
Diagnose what's causing unexpected traffic on switches
"""

import requests
import json
import time

FLOODLIGHT_CONTROLLER_URL = "http://localhost:8080"

def diagnose_traffic():
    print("=== Diagnosing Unexpected Traffic ===\n")
    
    # Get devices and their attachment points
    devices_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/device/')
    if devices_response.status_code != 200:
        print("Failed to get devices")
        return
        
    devices_data = devices_response.json()
    devices = devices_data.get('devices', [])
    
    # Build device mapping
    device_map = {}  # switch:port -> IP
    for device in devices:
        ipv4_addresses = device.get('ipv4', [])
        attachment_points = device.get('attachmentPoint', [])
        
        for ip in ipv4_addresses:
            if ip and ip != '0.0.0.0':
                for attachment in attachment_points:
                    switch_dpid = attachment.get('switch', '')
                    port_num = str(attachment.get('port', ''))
                    key = f"{switch_dpid}:{port_num}"
                    device_map[key] = ip
    
    print("Device-to-Port Mapping:")
    for key, ip in device_map.items():
        print(f"  {key} -> {ip}")
    print()
    
    # Get switches and analyze their port traffic
    switches_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json')
    if switches_response.status_code != 200:
        print("Failed to get switches")
        return
        
    switches = switches_response.json()
    
    print("Per-Port Traffic Analysis:")
    print("=" * 80)
    
    for switch in switches:
        switch_id = switch['switchDPID']
        print(f"\nSwitch {switch_id}:")
        
        port_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/port/json')
        
        if port_response.status_code == 200:
            port_data = port_response.json()
            ports = port_data.get('port_reply', [{}])[0].get('port', [])
            
            switch_total = 0
            port_details = []
            
            for port in ports:
                port_number = str(port.get('port_number', ''))
                if port_number != 'local':
                    rx_packets = int(port.get('receive_packets', 0))
                    tx_packets = int(port.get('transmit_packets', 0))
                    rx_bytes = int(port.get('receive_bytes', 0))
                    tx_bytes = int(port.get('transmit_bytes', 0))
                    
                    total_packets = rx_packets + tx_packets
                    total_bytes = rx_bytes + tx_bytes
                    
                    if total_packets > 0:
                        switch_total += total_packets
                        
                        # Check if this port has a device attached
                        port_key = f"{switch_id}:{port_number}"
                        device_ip = device_map.get(port_key, "No device")
                        
                        port_details.append({
                            'port': port_number,
                            'device': device_ip,
                            'rx_packets': rx_packets,
                            'tx_packets': tx_packets,
                            'total_packets': total_packets,
                            'total_bytes': total_bytes
                        })
            
            # Sort by total packets (highest first)
            port_details.sort(key=lambda x: x['total_packets'], reverse=True)
            
            print(f"  Total switch traffic: {switch_total:,} packets")
            print(f"  Port breakdown:")
            
            for detail in port_details:
                device_info = f"({detail['device']})" if detail['device'] != "No device" else "(Inter-switch)"
                print(f"    Port {detail['port']:>2}: {detail['total_packets']:>6,} packets "
                      f"(RX: {detail['rx_packets']:>4,}, TX: {detail['tx_packets']:>4,}) "
                      f"{device_info}")
        else:
            print(f"  Error getting port stats: {port_response.status_code}")
    
    print("\n" + "=" * 80)
    print("Analysis Summary:")
    print("- Ports with devices should show expected traffic")
    print("- Ports without devices showing high traffic indicate:")
    print("  * Inter-switch links (normal for network topology)")
    print("  * Broadcast/multicast traffic")
    print("  * Undetected devices or network issues")

if __name__ == "__main__":
    try:
        diagnose_traffic()
    except Exception as e:
        print(f"Error: {e}")
