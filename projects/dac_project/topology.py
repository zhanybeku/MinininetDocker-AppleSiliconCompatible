import json
import os
import time
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info


# Load configuration from JSON file:
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)


def topo():
    info("Creating network...\n")
    # Use the remote FloodLight controller:
    net = Mininet(controller=RemoteController, switch=OVSSwitch)

    # Load config to get controller info:
    config = load_config()
    controller_url = config['floodlight_controller_url']
    controller_ip = config['floodlight_controller_ip']
    controller_port = config['floodlight_controller_port']

    info(f"Adding controller (same as dac_app.py: {controller_url})...\n")
    # Create a single controller that all switches will connect to
    controller = net.addController(
        RemoteController("floodlight", ip=controller_ip, port=controller_port)
    )

    # Using the same topology as in PA2, but only one controller:
    num_blocks = 3
    switches_per_block = 3
    hosts_per_block = 3

    switches_by_block = [] # List of lists of switches in each block
    hosts_by_block = [] # List of lists of hosts in each block
    switch_objects = {} # Dictionary of switch objects by name
    host_objects = {} # Dictionary of host objects by name

    info("Adding switches and hosts...\n")
    for block_idx in range(num_blocks):
        block_switches = [] # List of switches in this block
        block_hosts = [] # List of hosts in this block

        # Add switches for this block
        for switch_idx in range(switches_per_block):
            switch_name = f"s{block_idx * switches_per_block + switch_idx + 1}"
            switch_obj = net.addSwitch(switch_name)
            # All switches connect to the same Floodlight controller
            switch_objects[switch_name] = switch_obj
            block_switches.append(switch_obj)

        # Add hosts for this block:
        for host_idx in range(hosts_per_block):
            host_num = block_idx * hosts_per_block + host_idx + 1
            host_name = f"h{host_num}"
            host_obj = net.addHost(host_name, ip=f"10.0.0.{host_num}/24")
            host_objects[host_name] = host_obj
            block_hosts.append(host_obj)

        switches_by_block.append(block_switches) # Add the list of switches to the list of lists of switches
        hosts_by_block.append(block_hosts) # Add the list of hosts to the list of lists of hosts

    info("Adding links...\n")
    for block_switches in switches_by_block: # For each block
        for i in range(len(block_switches)): # For each switch in the block
            for j in range(i + 1, len(block_switches)): # For every other switch in the block
                net.addLink(block_switches[i], block_switches[j]) # Add a link between the two switches

    # Add links between hosts and switches:
    for block_idx, (block_switches, block_hosts) in enumerate(
        zip(switches_by_block, hosts_by_block)
    ):
        for host_idx, host_obj in enumerate(block_hosts):
            switch_idx = host_idx % len(block_switches)
            net.addLink(host_obj, block_switches[switch_idx])

    # Add links between switches in different blocks:
    for block_idx in range(num_blocks - 1):
        switch_from = switches_by_block[block_idx][0]
        switch_to = switches_by_block[block_idx + 1][0]
        net.addLink(switch_from, switch_to)

    info("Starting network...\n")
    net.start()

    info("Assigning controllers to switches...\n")
    for switch_name, switch_obj in switch_objects.items():
        switch_obj.start([controller])

    info("Enabling STP on switches to prevent broadcast storms...\n")
    for switch_name, switch_obj in switch_objects.items():
        cmd = f"ovs-vsctl set Bridge {switch_name} stp_enable=true"
        switch_obj.cmd(cmd)
        info(f"  STP enabled on {switch_name}\n")

    info("Waiting for STP and controller learning to complete...\n")
    for i in range(10, 0, -1):
        info(f"  {i}... ")
        time.sleep(1)
    info("\nNetwork should be ready now!\n")

    # Update users.json with generated hosts
    info("Updating users.json with generated hosts...\n")
    users_data = []
    for host_name, host_obj in sorted(host_objects.items()):
        # Extract IP address (remove /24 subnet mask if present)
        host_ip = host_obj.IP().split('/')[0]
        users_data.append({
            "ip": host_ip,
            "role": "guest",
            "hostname": "default",
            "description": ""
        })
    
    users_json_path = os.path.join(os.path.dirname(__file__), 'users.json')
    with open(users_json_path, 'w') as f:
        json.dump(users_data, f, indent=2)
    info(f"  Updated users.json with {len(users_data)} hosts\n")

    CLI(net)

    info("Stopping network...\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    topo()
