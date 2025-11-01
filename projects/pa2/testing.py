from mininet.net import Mininet
from mininet.node import OVSSwitch, OVSController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def topo():
    info("Creating network...\n")
    net = Mininet(controller=OVSController, switch=OVSSwitch)

    info("Adding controllers...\n")
    controller = net.addController("c1")

    info("Adding switches...\n")
    switch1 = net.addSwitch("s1")
    switch2 = net.addSwitch("s2")
    switch3 = net.addSwitch("s3")

    info("Adding links...\n")
    net.addLink(switch1, switch2)
    net.addLink(switch1, switch3)
    net.addLink(switch2, switch3)

    info("Adding hosts...\n")
    host1 = net.addHost("h1")
    host2 = net.addHost("h2")
    host3 = net.addHost("h3")

    info("Adding links...\n")
    net.addLink(host1, switch1)
    net.addLink(host2, switch2)
    net.addLink(host3, switch3)

    info("Assigning controllers to switches...\n")
    switch1.start([controller])
    switch2.start([controller])
    switch3.start([controller])

    info("Starting network...\n")
    net.start()

    CLI(net)

    info("Stopping network...\n")
    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    topo()