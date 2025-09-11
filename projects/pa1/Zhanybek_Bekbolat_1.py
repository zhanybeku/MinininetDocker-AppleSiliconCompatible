from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

import subprocess

def install_flow_rules(net):
  h1_ip = net.get('h1').IP()
  h2_ip = net.get('h2').IP()
  h3_ip = net.get('h3').IP()
  h4_ip = net.get('h4').IP()
  h5_ip = net.get('h5').IP()
  h6_ip = net.get('h6').IP()
  
  info(f"h1_ip: {h1_ip}\n")
  info(f"h2_ip: {h2_ip}\n")
  info(f"h3_ip: {h3_ip}\n")
  info(f"h4_ip: {h4_ip}\n")
  info(f"h5_ip: {h5_ip}\n")
  info(f"h6_ip: {h6_ip}\n")
  
  # For s1:
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 arp,nw_dst={h1_ip},actions=output:1")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 arp,nw_dst={h2_ip},actions=output:2")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 arp,nw_dst={h3_ip},actions=output:4")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 arp,nw_dst={h4_ip},actions=output:3")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 arp,nw_dst={h5_ip},actions=output:3")
  
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 ip,nw_dst={h1_ip},actions=output:1")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 ip,nw_dst={h2_ip},actions=output:2")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 ip,nw_dst={h3_ip},actions=output:4")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 ip,nw_dst={h4_ip},actions=output:3")
  net.get('s1').cmd(f"ovs-ofctl add-flow s1 ip,nw_dst={h5_ip},actions=output:3")
  
  # For s2:
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 arp,nw_dst={h1_ip},actions=output:1")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 arp,nw_dst={h2_ip},actions=output:1")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 arp,nw_dst={h3_ip},actions=output:2")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 arp,nw_dst={h4_ip},actions=output:3")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 arp,nw_dst={h5_ip},actions=output:3")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 arp,nw_src={h3_ip},nw_dst={h6_ip},actions=output:4")
  
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 ip,nw_dst={h1_ip},actions=output:1")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 ip,nw_dst={h2_ip},actions=output:1")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 ip,nw_dst={h3_ip},actions=output:2")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 ip,nw_dst={h4_ip},actions=output:3")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 ip,nw_dst={h5_ip},actions=output:3")
  net.get('s2').cmd(f"ovs-ofctl add-flow s2 ip,nw_src={h3_ip},nw_dst={h6_ip},actions=output:4")
  
  # For s3:
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 arp,nw_dst={h1_ip},actions=output:2")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 arp,nw_dst={h2_ip},actions=output:2")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 arp,nw_dst={h3_ip},actions=output:4")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 arp,nw_dst={h4_ip},actions=output:1")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 arp,nw_dst={h5_ip},actions=output:3")
  
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 ip,nw_dst={h1_ip},actions=output:2")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 ip,nw_dst={h2_ip},actions=output:2")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 ip,nw_dst={h3_ip},actions=output:4")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 ip,nw_dst={h4_ip},actions=output:1")
  net.get('s3').cmd(f"ovs-ofctl add-flow s3 ip,nw_dst={h5_ip},actions=output:3")
  
  # For s4:
  net.get('s4').cmd(f"ovs-ofctl add-flow s4 arp,nw_dst={h6_ip},actions=output:3")
  net.get('s4').cmd(f"ovs-ofctl add-flow s4 arp,nw_src={h6_ip},nw_dst={h3_ip},actions=output:2")
  
  net.get('s4').cmd(f"ovs-ofctl add-flow s4 ip,nw_src={h3_ip},nw_dst={h6_ip},actions=output:3")
  net.get('s4').cmd(f"ovs-ofctl add-flow s4 ip,nw_src={h6_ip},nw_dst={h3_ip},actions=output:2")
  

def topo():
  info("Creating network...\n")
  net = Mininet(controller=None, switch=OVSSwitch)
  
  info("Adding hosts...\n")
  h1 = net.addHost('h1', ip='10.0.0.1/24')
  h2 = net.addHost('h2', ip='10.0.0.2/24')
  h3 = net.addHost('h3', ip='10.0.0.3/24')
  h4 = net.addHost('h4', ip='10.0.0.4/24')
  h5 = net.addHost('h5', ip='10.0.0.5/24')
  h6 = net.addHost('h6', ip='10.0.0.6/24')
  
  info("Adding switches...\n")
  s1 = net.addSwitch('s1')
  s2 = net.addSwitch('s2')
  s3 = net.addSwitch('s3')
  s4 = net.addSwitch('s4')
  
  info("Adding links...\n")
  net.addLink(s1, s2, port1=4, port2=1)
  net.addLink(s1, s3, port1=3, port2=2)
  net.addLink(s1, h1, port1=1)
  net.addLink(s1, h2, port1=2)
  
  net.addLink(s2, h3, port1=2)
  net.addLink(s2, s3, port1=3, port2=4)
  net.addLink(s2, s4, port1=4, port2=2)
  
  net.addLink(s3, h4, port1=1)
  net.addLink(s3, h5, port1=3)
  net.addLink(s3, s4, port1=5, port2=1)
  
  net.addLink(s4, h6, port1=3)
  
  info("Starting network...\n")
  net.start()
  
  info("Installing flow rules...\n")
  install_flow_rules(net)
  
  CLI(net)
  
  info("Stopping network...\n")
  net.stop()

if __name__ == '__main__':
  setLogLevel('info')
  topo()