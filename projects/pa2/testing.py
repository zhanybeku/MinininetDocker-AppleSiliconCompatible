from mn_wifi.net import Mininet_wifi
from mn_wifi.node import Station, OVSKernelAP
from mn_wifi.cli import CLI
from mininet.log import setLogLevel, info

def simpleTest():
    "Create a simple wireless network"
    net = Mininet_wifi()
    
    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', ip='10.0.0.1/24')
    sta2 = net.addStation('sta2', ip='10.0.0.2/24')
    ap1 = net.addAccessPoint('ap1', ssid='test-ssid', mode='g', channel='1')
    
    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()
    
    info("*** Creating links\n")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)
    
    info("*** Starting network\n")
    net.build()
    ap1.start([])
    
    info("*** Associating stations\n")
    sta1.setAssociation(ap1)
    sta2.setAssociation(ap1)
    
    info("*** Running CLI\n")
    CLI(net)
    
    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    simpleTest()