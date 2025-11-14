#!/usr/bin/env python3
"""
Test script to verify device-to-port mapping works correctly.
This script shows what the device API returns and how traffic is attributed.
"""

import requests
import json
import time

FLOODLIGHT_CONTROLLER_URL = "http://localhost:8080"

def test_device_mapping():
    """Test the device-to-port mapping approach"""
    
    print("=== Testing Device-to-Port Mapping ===\n")
    
    # Step 1: Get all switches
    print("1. Getting switches...")
    switches_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json')
    
    if switches_response.status_code != 200:
        print(f"Failed to get switches: {switches_response.status_code}")
        return
        
    switches = switches_response.json()
    print(f"Found {len(switches)} switches")
    
    # Step 2: Get all devices and their attachment points
    print("\n2. Getting devices and attachment points...")
    devices_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/device/')
    
    if devices_response.status_code != 200:
        print(f"Failed to get devices: {devices_response.status_code}")
        return
        
    devices_data = devices_response.json()
    devices = devices_data.get('devices', [])
    
    print(f"Found {len(devices)} total devices")
    
    # Filter IPv4 devices
    ipv4_devices = []
    for device in devices:
        ipv4_addresses = device.get('ipv4', [])
        if ipv4_addresses:
            ipv4_devices.append(device)
    
    print(f"Found {len(ipv4_devices)} IPv4 devices")
    
    # Step 3: Show device attachment mapping
    print("\n3. Device-to-Port Mapping:")
    for i, device in enumerate(ipv4_devices):
        ipv4_addresses = device.get('ipv4', [])
        attachment_points = device.get('attachmentPoint', [])
        mac_addresses = device.get('mac', [])
        
        print(f"\nDevice {i+1}:")
        print(f"  IP addresses: {ipv4_addresses}")
        print(f"  MAC addresses: {mac_addresses}")
        print(f"  Attachment points: {attachment_points}")
        
        if not attachment_points:
            print("  WARNING: No attachment points found!")
    
    # Step 4: Get port statistics for each switch
    print("\n4. Port Statistics per Switch:")
    switch_port_stats = {}
    
    for switch in switches:
        switch_id = switch['switchDPID']
        print(f"\nSwitch {switch_id}:")
        
        port_url = f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/switch/{switch_id}/port/json'
        port_response = requests.get(port_url)
        
        if port_response.status_code == 200:
            port_data = port_response.json()
            ports = port_data.get('port_reply', [{}])[0].get('port', [])
            
            for port in ports:
                port_number = port.get('port_number')
                if port_number != 'local' and port_number is not None:
                    rx_packets = int(port.get('receive_packets', 0))
                    tx_packets = int(port.get('transmit_packets', 0))
                    rx_bytes = int(port.get('receive_bytes', 0))
                    tx_bytes = int(port.get('transmit_bytes', 0))
                    
                    total_packets = rx_packets + tx_packets
                    total_bytes = rx_bytes + tx_bytes
                    
                    print(f"  Port {port_number}: {total_packets} packets, {total_bytes:,} bytes")
                    
                    # Store for mapping
                    switch_port_key = f"{switch_id}:{port_number}"
                    switch_port_stats[switch_port_key] = {
                        'total_packets': total_packets,
                        'total_bytes': total_bytes
                    }
        else:
            print(f"  Failed to get port stats: {port_response.status_code}")
    
    # Step 5: Show traffic attribution using new approach
    print("\n5. Traffic Attribution (New Approach):")
    
    for device in ipv4_devices:
        ipv4_addresses = device.get('ipv4', [])
        attachment_points = device.get('attachmentPoint', [])
        
        for ip in ipv4_addresses:
            if ip and ip != '0.0.0.0':
                device_bytes = 0
                device_packets = 0
                
                print(f"\nIP {ip}:")
                
                if not attachment_points:
                    print("  No attachment points - cannot attribute traffic")
                    continue
                
                for attachment in attachment_points:
                    switch_dpid = attachment.get('switch', '') or attachment.get('switchDPID', '')
                    port_num = attachment.get('port', '')
                    
                    switch_port_key = f"{switch_dpid}:{port_num}"
                    if switch_port_key in switch_port_stats:
                        port_stats = switch_port_stats[switch_port_key]
                        device_bytes += port_stats['total_bytes']
                        device_packets += port_stats['total_packets']
                        
                        print(f"  Connected to {switch_dpid}:{port_num}")
                        print(f"    Port traffic: {port_stats['total_packets']} packets, {port_stats['total_bytes']:,} bytes")
                    else:
                        print(f"  Connected to {switch_dpid}:{port_num} (no stats found)")
                
                print(f"  Total attributed traffic: {device_packets} packets, {device_bytes:,} bytes")

if __name__ == "__main__":
    try:
        test_device_mapping()
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        print("Make sure the Floodlight controller is running on localhost:8080")
    except Exception as e:
        print(f"Error: {e}")
