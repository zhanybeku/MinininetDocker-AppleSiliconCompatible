from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, RemoteController, OVSController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def topo():
  info("Creating network...\n")
  net = Mininet(controller=OVSController, switch=OVSSwitch)
  
  info("Adding hosts...\n")
  h1 = net.addHost("h1")
  h2 = net.addHost("h2")
  h3 = net.addHost("h3")
  h4 = net.addHost("h4")
  h5 = net.addHost("h5")
  h6 = net.addHost("h6")
  
  info("Adding switches...\n")
  s1 = net.addSwitch("s1")
  s2 = net.addSwitch("s2")
  s3 = net.addSwitch("s3")
  s4 = net.addSwitch("s4")
  s5 = net.addSwitch("s5")
  s6 = net.addSwitch("s6")
  s7 = net.addSwitch("s7")
  s8 = net.addSwitch("s8")
  
  info("Adding links...\n")
  net.addLink(s1, h1, port1=1)
  net.addLink(s1, s2, port1=2, port2=2)
  net.addLink(s1, s3, port1=3, port2=1)
  
  net.addLink(s2, h2, port1=1)
  net.addLink(s2, s6, port1=3, port2=2)
  net.addLink(s2, s4, port1=4, port2=1)
  
  net.addLink(s3, h3, port1=3)
  net.addLink(s3, s4, port1=2, port2=2)
  net.addLink(s3, s7, port1=4, port2=3)
  
  net.addLink(s5, s6, port1=1, port2=3)
  net.addLink(s5, s7, port1=2, port2=1)
  
  net.addLink(s6, h4, port1=1)
  net.addLink(s6, s8, port1=4, port2=1)
  
  net.addLink(s7, s8, port1=2, port2=3)
  
  net.addLink(s8, h5, port1=2)
  net.addLink(s8, h6, port1=4)
  
  info("Adding controllers...\n")
  c1 = net.addController('c1')
  c2 = net.addController('c2')
  
  info("Starting network...\n")
  net.start()

  c1.start()
  c2.start()
  
  info("Assigning controllers to switches...\n")
  s1.start([c1])
  s2.start([c1])
  s3.start([c1])
  s4.start([c1])
  
  s5.start([c2])
  s6.start([c2])
  s7.start([c2])
  s8.start([c2])
  
  CLI(net)
  
  info("Stopping network...\n")
  net.stop()

if __name__ == '__main__':
  setLogLevel('info')
  topo()