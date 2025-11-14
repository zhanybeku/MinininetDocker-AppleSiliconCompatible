#!/usr/bin/env python3
"""
Traffic analysis script to show the difference between active and passive traffic.
"""

import requests
import json
import time

FLOODLIGHT_CONTROLLER_URL = "http://localhost:8080"

def get_traffic_snapshot():
    """Get current traffic statistics for all devices"""
    
    # Get devices
    devices_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/device/')
    if devices_response.status_code != 200:
        return None
        
    devices_data = devices_response.json()
    devices = devices_data.get('devices', [])
    
    # Get switches  
    switches_response = requests.get(f'{FLOODLIGHT_CONTROLLER_URL}/wm/core/controller/switches/json')
    if switches_response.status_code != 200:
        return None
        
    switches = switches_response.json()
    
    # Build port stats lookup
    switch_port_stats = {}
    for switch in switches:
        switch_id = switch['switchDPID']
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
                    
                    switch_port_key = f"{switch_id}:{port_number}"
                    switch_port_stats[switch_port_key] = {
                        'total_packets': rx_packets + tx_packets,
                        'total_bytes': rx_bytes + tx_bytes
                    }
    
    # Map devices to traffic
    device_traffic = {}
    for device in devices:
        ipv4_addresses = device.get('ipv4', [])
        attachment_points = device.get('attachmentPoint', [])
        
        for ip in ipv4_addresses:
            if ip and ip != '0.0.0.0':
                device_bytes = 0
                device_packets = 0
                
                for attachment in attachment_points:
                    switch_dpid = attachment.get('switch', '') or attachment.get('switchDPID', '')
                    port_num = attachment.get('port', '')
                    
                    switch_port_key = f"{switch_dpid}:{port_num}"
                    if switch_port_key in switch_port_stats:
                        port_stats = switch_port_stats[switch_port_key]
                        device_bytes += port_stats['total_bytes']
                        device_packets += port_stats['total_packets']
                
                device_traffic[ip] = {
                    'packets': device_packets,
                    'bytes': device_bytes
                }
    
    return device_traffic

def analyze_traffic_changes():
    """Compare traffic before and after to see which devices are actually active"""
    
    print("=== Traffic Analysis ===")
    print("Taking baseline measurement...")
    
    baseline = get_traffic_snapshot()
    if not baseline:
        print("Failed to get baseline traffic")
        return
    
    print(f"Baseline traffic for {len(baseline)} devices:")
    for ip, stats in sorted(baseline.items()):
        print(f"  {ip}: {stats['packets']} packets, {stats['bytes']:,} bytes")
    
    print("\nWaiting 10 seconds for new traffic...")
    time.sleep(10)
    
    current = get_traffic_snapshot()
    if not current:
        print("Failed to get current traffic")
        return
    
    print("\nTraffic changes (delta):")
    print("=" * 50)
    
    changes = []
    for ip in baseline:
        if ip in current:
            packet_delta = current[ip]['packets'] - baseline[ip]['packets']
            byte_delta = current[ip]['bytes'] - baseline[ip]['bytes']
            
            changes.append({
                'ip': ip,
                'packet_delta': packet_delta,
                'byte_delta': byte_delta
            })
    
    # Sort by packet delta (most active first)
    changes.sort(key=lambda x: x['packet_delta'], reverse=True)
    
    for change in changes:
        if change['packet_delta'] > 0:
            print(f"🔥 {change['ip']}: +{change['packet_delta']} packets, +{change['byte_delta']:,} bytes (ACTIVE)")
        elif change['packet_delta'] == 0:
            print(f"💤 {change['ip']}: No change (IDLE)")
        else:
            print(f"📉 {change['ip']}: {change['packet_delta']} packets (DECREASED)")
    
    print("\n" + "=" * 50)
    active_hosts = [c for c in changes if c['packet_delta'] > 0]
    print(f"Summary: {len(active_hosts)} hosts with new traffic out of {len(changes)} total")

if __name__ == "__main__":
    try:
        analyze_traffic_changes()
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Error: {e}")
