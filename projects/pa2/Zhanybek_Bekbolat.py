# There are 5 blocks: 3, 4, 5, 6, 7
# Each block has a controller
# Far as I understand, each block has 3 switches and 2 access points
# - Not sure if we need to name the controllers with the block numbers specified or just starting from 1 is okay...

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info


def topo():
    info("Creating network...\n")
    net = Mininet(controller=None, switch=OVSSwitch)

    num_blocks = 5
    switches_per_block = 3
    hosts_per_block = 3

    controller_map = {}
    switches_by_block = []
    hosts_by_block = []
    switch_objects = {}
    host_objects = {}

    info("Adding controllers...\n")
    controller_ports = [6653, 6654, 6655, 6656, 6657]
    controller_objects = [
        net.addController(RemoteController(f"c{i + 1}", ip='127.0.0.1', port=controller_ports[i]))
        for i in range(num_blocks)
    ]
    
    for block_idx, controller in enumerate(controller_objects):
        block_switches = []
        block_hosts = []
        
        # Add switches for this block
        for switch_idx in range(switches_per_block):
            switch_name = f"s{block_idx * switches_per_block + switch_idx + 1}"
            switch_obj = net.addSwitch(switch_name)
            controller_map[switch_name] = [controller]
            switch_objects[switch_name] = switch_obj
            block_switches.append(switch_obj)
        
        # Add hosts for this block
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
    
    for block_idx, (block_switches, block_hosts) in enumerate(zip(switches_by_block, hosts_by_block)):
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
    for switch_name, controller_list in controller_map.items():
        switch_objects[switch_name].start(controller_list)

    info("Enabling STP on switches to prevent broadcast storms...\n")
    for switch_name, switch_obj in switch_objects.items():
        cmd = f"ovs-vsctl set Bridge {switch_name} stp_enable=true"
        switch_obj.cmd(cmd)
        info(f"  STP enabled on {switch_name}\n")
    
    import time
    info("Waiting for STP and controller learning to complete...\n")
    for i in range(10, 0, -1):
        info(f"  {i}... ")
        time.sleep(1)
    info("\nNetwork should be ready now!\n")

    CLI(net)

    info("Stopping network...\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    topo()
