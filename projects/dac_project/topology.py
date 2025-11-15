import json
import os
import time
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(config_path, 'r') as f:
        return json.load(f)


def topo():
    info("Creating network...\n")
    net = Mininet(controller=RemoteController, switch=OVSSwitch)

    config = load_config()
    controller_url = config['floodlight_controller_url']
    controller_ip = config['floodlight_controller_ip']
    controller_port = config['floodlight_controller_port']

    info(f"Adding controller (same as dac_app.py: {controller_url})...\n")
    controller = net.addController(
        RemoteController("floodlight", ip=controller_ip, port=controller_port)
    )

    num_blocks = 3
    switches_per_block = 3
    hosts_per_block = 3

    switches_by_block = []
    hosts_by_block = []
    switch_objects = {}
    host_objects = {}

    info("Adding switches and hosts...\n")
    for block_idx in range(num_blocks):
        block_switches = []
        block_hosts = []

        for switch_idx in range(switches_per_block):
            switch_name = f"s{block_idx * switches_per_block + switch_idx + 1}"
            switch_obj = net.addSwitch(switch_name)
            switch_objects[switch_name] = switch_obj
            block_switches.append(switch_obj)

        for host_idx in range(hosts_per_block):
            host_num = block_idx * hosts_per_block + host_idx + 1
            host_name = f"h{host_num}"
            host_obj = net.addHost(host_name, ip=f"10.0.0.{host_num}/24")
            host_objects[host_name] = host_obj
            block_hosts.append(host_obj)

        switches_by_block.append(block_switches)
        hosts_by_block.append(block_hosts)

    info("Adding links...\n")
    for block_switches in switches_by_block:
        for i in range(len(block_switches)):
            for j in range(i + 1, len(block_switches)):
                net.addLink(block_switches[i], block_switches[j])

    for block_idx, (block_switches, block_hosts) in enumerate(
        zip(switches_by_block, hosts_by_block)
    ):
        for host_idx, host_obj in enumerate(block_hosts):
            switch_idx = host_idx % len(block_switches)
            net.addLink(host_obj, block_switches[switch_idx])

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

    info("Updating users.json with generated hosts...\n")
    users_data = []
    
    role_map = {0: "admin", 1: "employee", 2: "guest"}
    
    for block_idx, block_hosts in enumerate(hosts_by_block):
        for host_idx, host_obj in enumerate(block_hosts):
            host_ip = host_obj.IP().split('/')[0]
            role = role_map.get(host_idx, "guest")
            users_data.append({
                "ip": host_ip,
                "role": role,
                "hostname": "default",
                "description": ""
            })
    
    users_data.sort(key=lambda x: x["ip"])
    
    users_json_path = os.path.join(os.path.dirname(__file__), 'users.json')
    with open(users_json_path, 'w') as f:
        json.dump(users_data, f, indent=2)
    info(f"  Updated users.json with {len(users_data)} hosts\n")
    info(f"  Role distribution: {sum(1 for u in users_data if u['role'] == 'admin')} admin, "
         f"{sum(1 for u in users_data if u['role'] == 'employee')} employee, "
         f"{sum(1 for u in users_data if u['role'] == 'guest')} guest\n")

    CLI(net)

    info("Stopping network...\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    topo()
