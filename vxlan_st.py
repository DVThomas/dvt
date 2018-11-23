#!/usr/bin/python
# -*- coding: utf-8 -*-

###################################################################
# connection_example.py : A test script example which includes:
#     common_seup section - device connection, configuration
#     Tescase section with testcase setup and teardown (cleanup)
#     subtestcase section with subtestcase setup and teardown (cleanup)
#     common_cleanup section - device cleanup
# The purpose of this sample test script is to show how to connect the
# devices/UUT in the common setup section. How to run few simple testcases
# (testcase might contain subtests).And finally, recover the test units in
# the common cleanup section. Script also provides an example on how to invoke
# TCL interpreter to call existing TCL functionalities.
###################################################################

#* Author: Danish Thomas
#* Feature Info : https://wiki.cisco.com/pages/viewpage.action?pageId=120270136
#*
#*   This feature is used to enable Vxlan P2P functionality on Trident based N9K & N3K(N9K mode only) TORs 
#*   This will enable tunnelling of all control frames (CDP, LLDP, LACP, STP, etc) across Vxlan cloud.
#*
#* ------------- V X L A N  TEST  T O P O L O G Y------------
#*
#*
#*
#*                      Evpn-Vtep-Simulator
#*                           ( Spirent )
#*                               |
#*                               |
#*                               |
#*                               |
#*                           +---+---+       +-------+
#*                           | spine1|       | spine2| 
#*                           |       |       |       |
#*                           +---+---+       +---+---+
#*                               |               |
#*        +--------------+-------+---------+-----+--------+-----------------+ 
#*        |              |                 |              |                 |                                    
#*    +-------+      +-------+         +-------+      +-------+         +---+---+             
#*    |       |      |       |         |       |      |       |         |       |             
#*    | leaf1 |<---->| leaf2 |         | leaf3 |      | leaf4 |         | leaf5 |              
#*    |       |      |       |         |       |      |       |         |       |              
#*    +---+---+      +---+---+         +-------+      +-------+         +---+---+              
#*        |  \          |   |           |   \          /     |              |                   
#*        |   \         |   |           |    \        /      |              |                     
#*        |    \        |   |           |     \      /      Orph4         Spirent              
#*        |     \       |   |          Orph3   esi x2      Spirent 
#*      Orp11    \      |   Orp21    Spirent    \  /
#*     Spirent    \     |   Spirent              \/
#*                 vpc x 2                
#*                   \ |                        SW2
#*                    \|                         |
#*            +-------------+             +-----------+
#*            |  switch 1   |             |  switch 2  |        
#*            +-----+-------+             +-----+-----+                                                  
#*                  |                           |
#*                  |                           |
#*                  |                           |
#*               Spirent                     Spirent 
#*                                              
#*             
#*                              
#*
#*
#*************************************************************************
 


import sys
import os
import pdb
import time
import json
import threading
from ats import aetest
#from ats.log.utils import banner
from ats import tcl
#import sth
from sth import StcPython


from ats import topology
#from dtcli import *

from vxlan_macmove_lib import *
from vxlan_xconnect_lib import *
from vxlan_lib import *

from ipaddress import *
from random import *
from string import *
import requests

#import re
from re import *
import logging
import general_lib
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

tcl.q.package('require', 'router_show')



from unicon.utils import Utils
from rest_util import RestAction
from routing_util import compare_string

# define variables scale numbers  feature list etc here

#vtep4 = vtep1 = vtep3 = vtep4  = sw1 = spine1 = port_handle1 = tgn1 =  0

## Scale number should be an even number

vlan_vni_scale = 400
tgn_rate=int(200000/vlan_vni_scale)
routing_vlan_scale = 10
mcast_group_scale = 10
ir_mode = 'mix'
#ir mode = 'bgp'  | 'mcast' | 'mix'

mac_scale = 20
if vlan_vni_scale*mac_scale > 60000:
    log.info(banner("-----MAC SCALE x VLAN VNI SCALE SHIULD BE LESS THAN 65000 --"))
    sys.exit(1)

vlan_start = 1001

bgp_ir_vlan_start=vlan_start
bgp_mcast_vlan_start=int(vlan_start+vlan_vni_scale/2)+1
vlan_scale_to_test=int(vlan_vni_scale/2)

vlan_end=vlan_start+vlan_vni_scale

traffic_to_be_tested_on_number_of_vlans= 5

tunnel_vlan_scale = 4
tunnel_vlan_start =  vlan_start

esi_id1 = '1001'
esi_id2 = '1022'
esi_id11 = '1011'
esi_id22 = '1222'
esi_mac1 = '0000.1001.1001'
esi_mac2 = '0000.1001.1022'
  
vlan_range=str(vlan_start)+"-"+str(vlan_end)
#str(tunnel_vlan_start+tunnel_vlan_scale+1)+"-"+str(vlan+vlan_vni_scale)

vxlan_traffic_test_vlan1=tunnel_vlan_start+tunnel_vlan_scale+2
vxlan_traffic_test_vlan2=vxlan_traffic_test_vlan1+1

log.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
log.info("vlan_vni_scale -------------------->%r",vlan_vni_scale)
log.info("routing_vlan_scale ---------------->%r",routing_vlan_scale)
#log.info("vlan ------------------------------>%r",vlan)
log.info("mac_scale ------------------------->%r",mac_scale)
log.info("vlan_start -------------------->%r",vlan_start)
log.info("vlan_end--------------------------->%r",vlan_end)
log.info("tunnel_vlan_scale------------------>%r",tunnel_vlan_scale)
log.info("tunnel_vlan_start------------------>%r",tunnel_vlan_start)
log.info("vlan_range--------------------->%r",vlan_range)
log.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

#pdb.set_trace() 

#tunnel_vlan_start = 1001

#vtep_emulation_spirent = 'yes'
#vtep_scale = 10

sw_feature_list = ['vrrp','private-vlan','port-security','interface-vlan','hsrp','lacp','lldp']
l3_feature_list = ['nv overlay','vn-segment-vlan-based','ospf','bgp','vtp','interface-vlan','bfd','pim','lacp']
anycastgw = "0000.2222.3333"
stp_mode = "mst"


pps=1000
rate=str(int(vlan_vni_scale)*pps) 
tol=int(float(rate)*0.015)

vtep_emulation_spirent = 'yes'
vtep_scale = 256

 
###################################################################
###                  COMMON SETUP SECTION                       ###
###################################################################

# Configure and setup all devices and test equipment in this section.
# This should represent the BASE CONFIGURATION that is applicable
# for the bunch of test cases that would follow.

class common_setup(aetest.CommonSetup):

    """ Common Setup for Sample Test """
 
    @aetest.subsection
    def testbed_init(self, testscript, testbed):
    #def connect(self, testscript, testbed):
        """ common setup subsection: connecting devices """

        global pps,rate,tol,tgen,tgen_port_handle_list,vtep1,vtep2,vtep3,vtep4,sw1,activePo1,vtep8,sw2,spine1,spine2,port_handle1,port_handle2,mac_scale2,tgn1_spine1_intf1,port_handle_spine1,\
        vtep3_spine1_intf1,vtep4_spine1_intf1,vlan_vni_scale,routing_vlan_scale,vlan_range,spine1_tgn1_intf1,uutList,vlan_range,esi_uut_list,\
        uut_list,vpc_uut_list,spine_uut_list,vtep_uut_list,l3_uut_list,vpc_uut_list,sw_uut_list,tgn1_sw1_intf1,vpc_uut_list,sa_vtep_uut_list,\
        port_handle_sw1,vtep_scale,vtep_emulation_spirent,leaf_tgn_ip,sw_feature_list,traffic_to_be_tested_on_number_of_vlans,port_handle_vtep5,\
        tunnel_vlan_start,tunnel_vlan_scale,tgn1_intf_list,tgn1_vtep3_intf1,tgn1_vtep5_intf1,tgn1_vtep1_intf1,port_handle_vtep1_1,port_handle_vtep1_1,mcast_group_scale,\
        labserver_ip,tgn_ip,port_handle_vtep2_1,port_handle_vtep2_1,port_handle_vtep1_2,tgn1_vtep3_intf2,tgn1_vtep1_intf2,tgn1_vtep4_intf1,tgn1_vtep2_intf1,\
        vpc_port_handle_list,xcon_po_port_handle_list,xcon_orphan_port_handle_list,port_handle_list,vxlan_traffic_test_vlan1,vxlan_traffic_test_vlan2,\
        main_uut_list,labserver_ip,tgn1_sw2_intf1,ir_mode,sw1_tgn1_intf1,vtep1_tgn1_intf1,vtep2_tgn1_intf1,\
        vtep3_tgn1_intf1,vtep4_tgn1_intf1,vtep5_tgn1_intf1,tgn1_spine1_intf1,\
        port_handle_sw1,port_handle_sw2,port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5 
        #vtep3 = testbed.devices['vtep3']
        #vtep4 = testbed.devices['vtep4']
        vtep1 = testbed.devices['vtep1']
        vtep2 = testbed.devices['vtep2']
        vtep3 = testbed.devices['vtep3']
        vtep4 = testbed.devices['vtep4']
        vtep5 = testbed.devices['vtep5'] 
   
        sw1 = testbed.devices['sw1']
        sw2 = testbed.devices['sw2']
        spine1 = testbed.devices['spine1']
        spine2 = testbed.devices['spine2']
        
        tgn = testbed.devices['tgn1']
        uut_list = [vtep1,vtep2,vtep3,vtep4,vtep5,sw1,sw2,spine1,spine2]
        l3_uut_list = [vtep1,vtep2,vtep3,vtep4,vtep5,spine1,spine2]     
        sw_uut_list = [sw1,sw2]
        vpc_uut_list = [vtep1,vtep2]
        esi_uut_list = [vtep3,vtep4]

        spine_uut_list = [spine1,spine2]
        vtep_uut_list = [vtep1,vtep2,vtep3,vtep4,vtep5]

        sa_vtep_uut_list = [vtep5] 
        
        sw1_tgn1_intf1 = testbed.devices['sw1'].interfaces['sw1_tgn1_intf1'].intf
        sw2_tgn1_intf1 = testbed.devices['sw2'].interfaces['sw2_tgn1_intf1'].intf
                
        vtep1_tgn1_intf1 = testbed.devices['vtep1'].interfaces['vtep1_tgn1_intf1'].intf
        vtep2_tgn1_intf1 = testbed.devices['vtep2'].interfaces['vtep2_tgn1_intf1'].intf        
        vtep3_tgn1_intf1 = testbed.devices['vtep3'].interfaces['vtep3_tgn1_intf1'].intf
        vtep4_tgn1_intf1 = testbed.devices['vtep4'].interfaces['vtep4_tgn1_intf1'].intf
        vtep5_tgn1_intf1 = testbed.devices['vtep5'].interfaces['vtep5_tgn1_intf1'].intf

        

        tgn1_sw1_intf1 = testbed.devices['tgn1'].interfaces['tgn1_sw1_intf1'].intf
        tgn1_sw2_intf1 = testbed.devices['tgn1'].interfaces['tgn1_sw2_intf1'].intf

        tgn1_spine1_intf1 = testbed.devices['tgn1'].interfaces['tgn1_spine1_intf1'].intf

        tgn1_vtep1_intf1 = testbed.devices['tgn1'].interfaces['tgn1_vtep1_intf1'].intf
        tgn1_vtep2_intf1 = testbed.devices['tgn1'].interfaces['tgn1_vtep2_intf1'].intf
        tgn1_vtep3_intf1 = testbed.devices['tgn1'].interfaces['tgn1_vtep3_intf1'].intf
        tgn1_vtep4_intf1 = testbed.devices['tgn1'].interfaces['tgn1_vtep4_intf1'].intf
        tgn1_vtep5_intf1 = testbed.devices['tgn1'].interfaces['tgn1_vtep5_intf1'].intf  

        labserver_ip = str(testbed.devices['tgn1'].connections['labsvr'].ip)
        tgn_ip = str(testbed.devices['tgn1'].connections['a'].ip)
       
        
        tgn1_intf_list = []
        for key in testbed.devices['tgn1'].interfaces.keys():
            intf = testbed.devices['tgn1'].interfaces[key].intf
            tgn1_intf_list.append(intf)
            
        log.info(banner("~~~~~~~~~~~Clearing C O N S O L E Connections~~~~~~~~~~~"))   
 
    
  
    @aetest.subsection
    def connect(self, testscript, testbed):   
           
        for uut in uut_list:
            if 'port' in uut.connections['a']:
                ts = str(uut.connections['a']['ip'])
                port=str(uut.connections['a']['port'])[-2:]
                log.info('UUT %r console clearing terminal server is %r and port is %r',str(uut),ts,str(uut.connections['a']['port']))                
                u = Utils()
                u.clear_line(ts, port, 'lab', 'lab')


        for uut in uut_list:
            print('uut = %s' % uut)
            try:
                uut.connect()
            except:
                self.failed(goto=['common_cleanup'])
                
            if not hasattr(uut, 'execute'):
                #self.failed(goto=['common_cleanup'])
                self.failed(goto=['common_cleanup'])
            if uut.execute != uut.connectionmgr.default.execute:
                #self.failed(goto=['common_cleanup'])
                self.failed(goto=['common_cleanup'])
            #uut.set_csccon_default(boot_timeout=900) 
    
    @aetest.subsection
    def tcam_check(self, testscript, testbed):
        for uut in vtep_uut_list: 
            op = uut.execute('sh hardware access-list tcam region | incl vpc-c')
            if 'size =    0' in op:
                self.failed(goto=['common_cleanup']) 
            op = uut.execute('sh hardware access-list tcam region | incl arp-eth')
            if 'size =    0' in op:
                self.failed(goto=['common_cleanup'])    
       
    
    @aetest.subsection
    def pre_clean(self, testscript, testbed):
        
        log.info(banner("Clean the testbed configuration"))
        threads = [] 
        clean1 =\
            """
                no int nve 1
                no feature ngoam
                no feature nv over
                no feature bgp
                no feature ospf
                no feature pim
                no feature interface-vlan
                no vlan 2-1501
                feature nv over
                feature bgp
                feature ospf
                feature pim
                feature interface-vlan  
                nv overlay evpn
                feature vn-segment-vlan-based  


            """
            
        for uut in l3_uut_list:
            t = threading.Thread(target=DevicePreCleanup, args=(uut,))        
            threads.append(t)
        for t in threads: 
            t.start()
        for t in threads: 
            t.join()


        for uut in sw_uut_list:
            SwPreCleanup(uut) 
         
        log.info("Testbed pre-clean passed")
  
    @aetest.subsection
    def base_configs(self, testscript, testbed): 
         
        log.info(banner("Base configurations"))
       
        cfg = \
            """
            spanning-tree mode mst
            no spanning-tree mst configuration
            feature lacp
            no ip igmp snooping
            no vlan 2-3831
            terminal session-timeout 0
            """
        for uut in uut_list:
            uut.configure(cfg)

        log.info(banner("NV Overlay configurations"))
        
        cfg = \
            """
            nv overlay evpn
            fabric forwarding anycast-gateway-mac {gw}
            """
        for uut in vtep_uut_list:
            uut.configure(cfg.format(gw=anycastgw))

        for uut in spine_uut_list:
            uut.configure('nv overlay evpn')
 
      
        log.info(banner("Configuring loopbacks in VPC switches"))  
             
        for uut in vpc_uut_list:
            for intf in uut.interfaces.keys():
                if 'loopback' in intf:
                    if 'loopback0' in intf:
                        intf=uut.interfaces[intf].intf                        
                        ipv4_add=uut.interfaces[intf].ipv4
                        ipv4_add_sec=uut.interfaces[intf].ipv4_sec
                        try:
                            config_loopback(uut,intf,ipv4_add,ipv4_add_sec)
                        except:
                            log.info('Loopback configuration failed in device : %r',uut) 
                            self.failed(goto=['common_cleanup']) 
 
                    else:
                        intf=uut.interfaces[intf].intf
                        ipv4_add=uut.interfaces[intf].ipv4
                        
                        try:
                            config_loopback(uut,intf,ipv4_add,"Nil")
                        except:
                            log.info('Loopback configuration failed in device : %r',uut) 
                            self.failed(goto=['common_cleanup']) 

        
        log.info(banner("Configuring loopbacks in SA VTEP switches"))     
        for uut in sa_vtep_uut_list:
            for intf in uut.interfaces.keys():
                if 'loopback' in intf:
                        intf=uut.interfaces[intf].intf
                        ipv4_add=uut.interfaces[intf].ipv4
                        try:
                            config_loopback(uut,intf,ipv4_add,"Nil")
                        except:
                            log.info('Loopback configuration failed in device : %r',uut) 
                            self.failed(goto=['common_cleanup']) 

        log.info(banner("Configuring loopbacks in SA VTEP switches"))     
        for uut in esi_uut_list:
            for intf in uut.interfaces.keys():
                if 'loopback' in intf:
                        intf=uut.interfaces[intf].intf
                        ipv4_add=uut.interfaces[intf].ipv4
                        try:
                            config_loopback(uut,intf,ipv4_add,"Nil")
                        except:
                            log.info('Loopback configuration failed in device : %r',uut) 
                            self.failed(goto=['common_cleanup']) 


        log.info(banner("Configuring loopbacks in Spine switches"))
        for uut in spine_uut_list:
            for intf in uut.interfaces.keys():
                if 'loopback' in intf:
                    intf=uut.interfaces[intf].intf
                    ipv4_add=uut.interfaces[intf].ipv4
                    try:
                        config_loopback(uut,intf,ipv4_add,"Nil")
                    except:
                        log.info('Loopback configuration failed in device : %r',uut) 
                        self.failed(goto=['common_cleanup']) 
         
  
    @aetest.subsection
    def l3_po_configs(self, testscript, testbed):         
        log.info("Configuring L3 Port Channels")
        for uut in l3_uut_list:
            po_member_list = []
            for intf in uut.interfaces.keys():
                if 'Eth' in uut.interfaces[intf].intf:
                    if 'Po' in uut.interfaces[intf].alias:
                        po_member_list.append(intf)

                log.info('l3 po mem list for uut %r is %r',str(uut),po_member_list)      
                                  
            for intf in uut.interfaces.keys():
                if 'l3_po' in uut.interfaces[intf].type:
                    Po = uut.interfaces[intf].intf
                    ipv4_add = uut.interfaces[intf].ipv4
                    
                    po_mem_list=[]
                    for intf in po_member_list:
                        member = uut.interfaces[intf].alias
                        if member.strip("Po") == Po:
                            po_mem_list.append(uut.interfaces[intf].intf)                                  
                    log.info('l3 po mem list for po %r uut %r is %r',Po,str(uut),po_mem_list)   
                    uut_l3Po_obj = CLI_PortChannel(uut,Po,'Nil','layer3',po_mem_list,ipv4_add)
                    uut_l3Po_obj.ConfigurePo()
        
                     
        countdown(80)
        
      
        for uut in l3_uut_list:
            op=uut.execute('show port-channel summary | incl Eth')
            op1=op.splitlines()
            for line in op1:
                if line:
                    if not "(P)" in line:
                        log.info('L3 port Channel Bringup Failed on device %r',str(uut)) 
                        uut.execute('show port-channel summary')
                        #self.failed
                        self.failed(goto=['common_cleanup'])
  
    @aetest.subsection
    def ospf_configs(self, testscript, testbed):  
        log.info("Configuring OSPF and adding interfaces")
        for uut in l3_uut_list:
            intf_list=[]
            for intf in uut.interfaces.keys():
                if 'l3_po' in uut.interfaces[intf].type:
                    intf= 'Port-Channel' + uut.interfaces[intf].intf
                    intf_list.append(intf)

                if 'loopback' in intf:
                    if not 'loopback0' in intf:
                        if 'loopback1' in intf:
                            intf = uut.interfaces[intf].intf
                            ospf_rid=(str(uut.interfaces[intf].ipv4))[:-3]
                            intf_list.append(intf)
                        else:
                            intf = uut.interfaces[intf].intf
                            intf_list.append(intf)

            uut_ospf_obj=OspfV4Router(uut,'1',ospf_rid,intf_list)
            uut_ospf_obj.ospf_conf()
     
    @aetest.subsection
    def pim_configs(self, testscript, testbed):  
                              
        log.info("Configuring PIM and adding interfaces")
        rp_add = (str(testbed.devices['spine1'].interfaces['loopback2'].ipv4))[:-3]
        log.info("RP Address isssss %r",rp_add)
        try: 
             
            for uut in l3_uut_list:
                intf_list=[]
                for intf in uut.interfaces.keys():
                    if 'l3_po' in uut.interfaces[intf].type:
                        intf= 'Port-Channel' + uut.interfaces[intf].intf
                        intf_list.append(intf)

                    if 'loopback' in intf:
                            intf = uut.interfaces[intf].intf
                            intf_list.append(intf)
                
                uut_pim_obj=PimV4Router(uut,rp_add,intf_list) 
                uut_pim_obj.pim_conf()


        except:
            log.info("PIMv4 configuration failed") 
            self.failed(goto=['common_cleanup'])


        log.info(banner("Configuring PIM Anycast")) 
 
        log.info(banner("Configuring PIM Anycast")) 
        #for uut in spine_uut_list:
        ip1 = (str(testbed.devices['spine1'].interfaces['loopback1'].ipv4))[:-3]
        ip2 = (str(testbed.devices['spine2'].interfaces['loopback1'].ipv4))[:-3]

        cfg = \
            """
            ip pim ssm range 232.0.0.0/8
            ip pim anycast-rp {rp_add} {ip1}
            ip pim anycast-rp {rp_add} {ip2}
            """

        for uut in spine_uut_list:
            try:
                uut.configure(cfg.format(rp_add=rp_add,ip1=ip1,ip2=ip2))
            except:
                log.info("PIM ANYCAST configuration failed") 
                self.failed(goto=['common_cleanup'])

    @aetest.subsection
    def igp_verify(self, testscript, testbed):  
                              
        countdown(45) 
          
        log.info(banner("Starting OSPF / PIM verify Section"))       
        for uut in l3_uut_list:
            for feature in ['ospf','pim']:
                test1 = leaf_protocol_check222(uut,[feature])
                if not test1:
                    log.info('Feature %r neigborship on device %r Failed ',feature,str(uut))
                    self.failed(goto=['common_cleanup'])             
        
 
    @aetest.subsection
    def standalone_vtep_tgn_port_configs(self, testscript, testbed):
        log.info(banner("Configuring SA VTEP TGN Ports"))     
        for uut in sa_vtep_uut_list:
            for intf in uut.interfaces.keys():
               if 'tgn1_intf1' in intf:
                    intf = uut.interfaces[intf].intf
                    cfg = """\
                        interface {intf}
                        switchport
                        switchport mode trunk
                        switchport trunk allowed vlan {vlan_range}
                        spanning-tree bpdufilter enable
                        spanning-tree port type edge trunk 
                        no shut
                        """
                    try:    
                        uut.configure(cfg.format(intf=intf,vlan_range=vlan_range))
                    except:
                        log.info("Switch TGN Port Configuration Failed")
                        self.failed(goto=['common_cleanup'])
 
    @aetest.subsection
    def vpc_esi_vtep_orphan_port_configs(self, testscript, testbed):
        for uut in vtep_uut_list:
            for intf in uut.interfaces.keys():
                if 'Orphan' in uut.interfaces[intf].alias:
                    intf = uut.interfaces[intf].intf
                    cfg = """\
                        interface {intf}
                        switchport
                        switchport mode trunk
                        switchport trunk allowed vlan {vlan_range}
                        spanning-tree port type edge trunk 
                        spanning-tree bpdufilter enable
                        no shut
                        """                    
                    try:    
                        uut.configure(cfg.format(intf=intf,vlan_range=vlan_range))
                    except:
                        log.info("UUT  %r TGN Port Configuration Failed",uut)
                        self.failed(goto=['common_cleanup'])

 
    @aetest.subsection
    def sw_po_bringup(self, testscript, testbed):
        log.info("Configuring Port Channels in Switch and adding interfaces for vPC/TGN")        
        for uut in sw_uut_list:
            sw_po_member_list = [] 
            for intf in uut.interfaces.keys():
                if 'Eth' in uut.interfaces[intf].intf:
                    if 'Po' in uut.interfaces[intf].alias:
                        sw_po_member_list.append(intf)
                        
            for intf in uut.interfaces.keys():
                if 'po_to_vtep' in uut.interfaces[intf].type:  
                    Po = uut.interfaces[intf].intf   
                    vlan = vlan_range
                    mode = uut.interfaces[intf].mode
                    sw_po_members = []
                    for intf in sw_po_member_list:
                        member = uut.interfaces[intf].alias
                        if member.strip("Po") == Po:
                            sw_po_members.append(uut.interfaces[intf].intf) 

                    sw_po_obj = CLI_PortChannel(uut,Po,vlan,mode,sw_po_members,'Nil')                     
                    sw_po_obj.ConfigurePo()
        
        for uut in sw_uut_list:
            for intf in uut.interfaces.keys():
                if 'tgn' in uut.interfaces[intf].alias:
                    intf = uut.interfaces[intf].intf
                    cfg = """\
                        interface {intf}
                        switchport
                        switchport mode trunk
                        switchport trunk allowed vlan {vlan_range}
                        spanning-tree bpdufilter enable
                        spanning-tree port type edge trunk 
                        no shut
                        """
                    print(cfg.format(intf=intf,vlan_range=vlan_range))
                    
                    try:    
                        uut.configure(cfg.format(intf=intf,vlan_range=vlan_range))
                    except:
                        log.info("Switch TGN Port Configuration Failed")
                        self.failed(goto=['common_cleanup'])
 

 

 
    @aetest.subsection
    def vpc_global_configs(self, testscript, testbed):
        log.info(banner("VPC configurations"))  
          
        for uut in vpc_uut_list:
            mct_member_list = [] 
            for intf in uut.interfaces.keys():
                if 'Eth' in uut.interfaces[intf].intf:
                    if 'mct' in uut.interfaces[intf].alias:
                        mct_member_list.append(uut.interfaces[intf].intf) 

            for intf in uut.interfaces.keys():
                if 'mct_po' in uut.interfaces[intf].type:
                    mct_po = uut.interfaces[intf].intf
                    peer_ip = uut.interfaces[intf].peer_ip
                    src_ip = uut.interfaces[intf].src_ip                     
                    vtep_vpc_global_obj1 = VPCNodeGlobal(uut,mct_po,peer_ip,mct_member_list,src_ip)         
                    vtep_vpc_global_obj1.vpc_global_conf()
    
    @aetest.subsection
    def vpc_po_bringup(self, testscript, testbed):
        log.info(banner("VPC configurations"))  

        for uut in vpc_uut_list:
            vpc_po_member_list = [] 
            for intf in uut.interfaces.keys():
                if 'Eth' in uut.interfaces[intf].intf:
                    if 'Po' in uut.interfaces[intf].alias:
                        vpc_po_member_list.append(intf) 
            

            #pdb.set_trace()            
            for intf in uut.interfaces.keys():
                if 'vpc_po' in uut.interfaces[intf].type:
                    Po = uut.interfaces[intf].intf
                    mode = uut.interfaces[intf].mode                   
                    vpc_members = []

                    for intf in vpc_po_member_list:
                        member = uut.interfaces[intf].alias
                        if member.strip("Po") == Po:
                            intf=uut.interfaces[intf].intf
                            vpc_members.append(intf) 
                     
                    vtep_vpc_obj1 = VPCPoConfig(uut,Po,vpc_members,vlan_range,mode)         
                    vtep_vpc_obj1.vpc_conf()
     
     

 
    @aetest.subsection
    def l3_svi_bringup(self, testscript, testbed):
        log.info(banner("Adding L3 SVI for vTEP's"))
        """
        To provide redundancy and failover of VXLAN traffic when a VTEP loses all of its uplinks to the spine, \
        it is recommended to run a Layer 3 link or an SVI link over the peer-link between VPC peers.
        https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/7-x/vxlan/configuration/guide
        b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide_7x/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration
        _Guide_7x_chapter_0100.html#reference_2D1F5BD4C66A45D9A40DFCF030EF1ED7
        """
        for uut in vpc_uut_list:   
            for intf in uut.interfaces.keys():               
                if 'svi1' in intf:
                    svi = uut.interfaces[intf].intf
                    ipv4 = uut.interfaces[intf].ipv4
            cfg = \
                    """
                    vlan 2
                    no interface vlan2
                    interface vlan2
                    mtu 9216
                    ip address {ipv4}
                    ip router ospf 1 area 0
                    no shut
                    """
            try:
                uut.configure(cfg.format(ipv4=ipv4))
            except:
                log.info("vTEP L3 SVI for VPC Configuration Failed @ uut %r",uut)
                self.failed(goto=['common_cleanup'])



    @aetest.subsection
    def vpc_verify(self, testscript, testbed):       
        countdown(90)
       
        for uut in vpc_uut_list:
            op=uut.execute('show port-channel summary | incl Eth')
            op1=op.splitlines()
            for line in op1:
                if line:
                    if not "(P)" in line:
                        log.info('VPC Bringup Failed on device %r',str(uut)) 
                        uut.execute('show port-channel summary')
                        self.failed(goto=['common_cleanup'])
         
  
    @aetest.subsection
    def bgp_configurations(self, testscript, testbed):
        log.info(banner("BGP configurations"))
        
        #threads=  []
        neight_list_leaf =[]         
        for uut in spine_uut_list:      
            for intf in uut.interfaces.keys():
                if 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    spine_neigh=(str(uut.interfaces[intf].ipv4))[:-3]
                    neight_list_leaf.append(spine_neigh)

            for intf in uut.interfaces.keys():
                if 'tgn1_intf1' in intf:
                    intf_1 = uut.interfaces[intf].intf
                    ipv4_1 = uut.interfaces[intf].ipv4
                    cfg = """\
                        interface {intf}
                        no switchport
                        ip address {ipv4}
                        no shut
                        """
                    uut.configure(cfg.format(intf=intf_1,ipv4=ipv4_1))

                    
    @aetest.subsection
    def bgp_configurations(self, testscript, testbed):
        log.info(banner("BGP configurations"))

        neight_list_leaf =[]         
        for uut in spine_uut_list:      
            for intf in uut.interfaces.keys():
                if 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    spine_neigh=(str(uut.interfaces[intf].ipv4))[:-3]
                    neight_list_leaf.append(spine_neigh)

            for intf in uut.interfaces.keys():
                if 'tgn1_intf1' in intf:
                    intf_1 = uut.interfaces[intf].intf
                    ipv4_1 = uut.interfaces[intf].ipv4
                    cfg = """\
                        interface {intf}
                        no switchport
                        ip address {ipv4}
                        no shut
                        """
                    uut.configure(cfg.format(intf=intf_1,ipv4=ipv4_1))


        for uut in sa_vtep_uut_list:
            uut.configure("no feature vpc")
            countdown(5)
            adv_nwk_list =[]
            for intf in uut.interfaces.keys():
                if 'loopback0' in intf:
                    intf = uut.interfaces[intf].intf
                    nwk1 = uut.interfaces[intf].ipv4
                    adv_nwk_list.append(nwk1)

                elif 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    upd_src = intf
                    bgp_rid=(str(uut.interfaces[intf].ipv4))[:-3]

            #try:  
            leaf_bgp_obj=IbgpLeafNode(uut,bgp_rid,'65001',adv_nwk_list,neight_list_leaf,upd_src,'ibgp-vxlan')
            leaf_bgp_obj.bgp_conf()
        
        neight_list_spine =[]

            
        log.info("neight_list_leaf -----for uut %r",neight_list_leaf) 
        for uut in vpc_uut_list:
            adv_nwk_list =[]
            for intf in uut.interfaces.keys():
                if 'loopback0' in intf:
                    intf = uut.interfaces[intf].intf
                    nwk1 = uut.interfaces[intf].ipv4
                    adv_nwk_list.append(nwk1)
                    nwk2 = uut.interfaces[intf].ipv4_sec
                    adv_nwk_list.append(nwk2)

                elif 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    upd_src = intf
                    bgp_rid=(str(uut.interfaces[intf].ipv4))[:-3]

            #try:  
            leaf_bgp_obj=IbgpLeafNode(uut,bgp_rid,'65001',adv_nwk_list,neight_list_leaf,upd_src,'ibgp-vxlan')
            leaf_bgp_obj.bgp_conf()

                   
        log.info("neight_list_leaf -----for uut %r",neight_list_leaf) 
      
        for uut in esi_uut_list:
            uut.configure("no feature vpc")
            countdown(5)
            adv_nwk_list =[]
            for intf in uut.interfaces.keys():
                if 'loopback0' in intf:
                    intf = uut.interfaces[intf].intf
                    nwk1 = uut.interfaces[intf].ipv4
                    adv_nwk_list.append(nwk1)

                elif 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    upd_src = intf
                    bgp_rid=(str(uut.interfaces[intf].ipv4))[:-3]

            #try:  
            leaf_bgp_obj=IbgpLeafNode(uut,bgp_rid,'65001',adv_nwk_list,neight_list_leaf,upd_src,'ibgp-vxlan')
            leaf_bgp_obj.bgp_conf()
        
        neight_list_spine =[]

        for uut in vtep_uut_list:      
            for intf in uut.interfaces.keys():
                if 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    leaf_neigh=(str(uut.interfaces[intf].ipv4))[:-3]
                    neight_list_spine.append(leaf_neigh)

        log.info("neight_list -----for uut %r",neight_list_spine) 

        for uut in spine_uut_list:
            adv_nwk_list =[]
            for intf in uut.interfaces.keys():
                if 'loopback0' in intf:
                    intf = uut.interfaces[intf].intf
                    nwk1 = uut.interfaces[intf].ipv4
                    adv_nwk_list.append(nwk1)

                elif 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    upd_src = intf
                    bgp_rid=(str(uut.interfaces[intf].ipv4))[:-3]
                
            spine_bgp_obj=IbgpSpineNode(uut,bgp_rid,'65001',adv_nwk_list,neight_list_spine,upd_src,'ibgp-vxlan')
            spine_bgp_obj.bgp_conf()
   
 
    @aetest.subsection
    def common_verify(self, testscript, testbed):
        countdown(60)
     
        log.info(banner("Starting Common verify Section"))       
        for uut in vtep_uut_list:
            for feature in ['ospf','pim','bgp']:
                test1 = leaf_protocol_check222(uut,[feature])
                if not test1:
                    log.info('Feature %r neigborship on device %r Failed ',feature,str(uut))
                    self.failed(goto=['common_cleanup'])
 
    @aetest.subsection
    def vxlan_configs(self, testscript, testbed):
        log.info(banner("VXLAN configurations")) 
        threads = []           
        for uut in vtep_uut_list:
            for intf in uut.interfaces.keys():
                if 'vxlan' in intf:
                    intf = uut.interfaces[intf].intf
                    vni=201001
                    routed_vlan = 101
                    routed_vni = 90100
                    ipv4_add1 = (str(uut.interfaces[intf].ipv4_add))[:-3]
                    ipv4_add = sub("/(.*)",'',ipv4_add1)
                    ipv6_add1 = (str(uut.interfaces[intf].ipv6_add))[:-4]
                    ipv6_add = sub("/(.*)",'',ipv6_add1)
                    log.info("IR mode is ================= %r",ir_mode)
                    mcast_group = (str(uut.interfaces[intf].mcast_group))[:-3]
                    vtep_vxlan_obj1=LeafObject2222(uut,vlan_start,vni,vlan_vni_scale,routed_vlan,routed_vni,routing_vlan_scale,ipv4_add,ipv6_add,mcast_group,'65001',ir_mode,mcast_group_scale)
                    t = threading.Thread(target=vtep_vxlan_obj1.vxlan_conf())
                    threads.append(t)
 
        for t in threads: 
            t.start()
        for t in threads: 
            t.join()
 
    @aetest.subsection
    def esi_bringup(self, testscript, testbed):
        log.info(banner("ESI configurations"))  
        threads = []  
        for uut in esi_uut_list:
            try:
                ConfigureEsiGlobal(uut)
            except:
                log.info('ConfigureEsiGlobal failed in uut %r',uut)
                self.failed(goto=['common_cleanup'])

        for uut in esi_uut_list:
            esi_po_member_list = [] 
            for intf in uut.interfaces.keys():
                if 'Eth' in uut.interfaces[intf].intf:
                    if 'Po' in uut.interfaces[intf].alias:
                        esi_po_member_list.append(intf)
                        
            for intf in uut.interfaces.keys():
                if 'esi_po' in uut.interfaces[intf].type:
                    Po = uut.interfaces[intf].intf
                    esid = uut.interfaces[intf].esid
                    sys_mac = uut.interfaces[intf].sys_mac
                    mode = uut.interfaces[intf].mode
                    esi_members = []
                    for intf in esi_po_member_list:
                        member = uut.interfaces[intf].alias
                        if member.strip("Po") == Po:
                            esi_members.append(uut.interfaces[intf].intf)
                    try:
                        vtep_esi_obj1 = EsiNode(uut,esid,sys_mac,Po,esi_members,vlan_range,mode)        
                        vtep_esi_obj1.esi_configure()
                    #t = threading.Thread(target= vtep_esi_obj1.esi_configure)
                    #threads.append(t)
                         
                    except:
                        log.info('ESI Configs failed')
                        self.failed(goto=['common_cleanup'])

        for uut in esi_uut_list:
            intf_list=[]
            for intf in uut.interfaces.keys():
                if 'l3_po' in uut.interfaces[intf].type:
                    intf= 'Port-Channel' + uut.interfaces[intf].intf
                    intf_list.append(intf)
            for intf in intf_list:
                cfg = \
                """
                interface {intf}
                evpn multihoming core-tracking
                """
                uut.configure(cfg.format(intf=intf))
    
    @aetest.subsection
    def esi_verify(self, testscript, testbed):       
        countdown(90)
       
        for uut in esi_uut_list:
            op=uut.execute('show port-channel summary | incl Eth')
            op1=op.splitlines()
            for line in op1:
                if line:
                    if not "(P)" in line:
                        log.info('VPC Bringup Failed on device %r',str(uut)) 
                        uut.execute('show port-channel summary')
                        self.failed(goto=['common_cleanup'])


        log.info(banner(" SHUTING REDUNDANT ACCESS PO ")) 
        cfg = \
            """
            int port-channel 102
            shut
            """
            
        
        for uut in vpc_uut_list+esi_uut_list:
            uut.configure(cfg)


     
    @aetest.subsection
    def configureTgn(self, testscript, testbed):
        """ common setup subsection: connecting devices """

        global tgen, tgen_port_handle_list, vtep1, vtep2, vtep3, vtep4,vtep1,vtep2, \
            sw1, sw2, spine1, port_handle1, port_handle2, port_handle,labserver_ip,port_list,\
            port_hdl_list,ip_src_list,ip_dst_list,mac_src_list,mac_dst_list,stream_list,port_handle_sw1,port_handle_sw2,\
            port_handle_spine1,vtep_scale,tgn1_intf_list,port_handle_vtep1,port_handle_vtep2,\
            port_handle_vtep2_1,port_handle_vtep2_1,port_handle_vtep1_2,port_handle_vtep1_2,\
            vpc_port_handle_list,port_handle_list,tgn1_vtep7_intf1,port_handle_vtep4,port_handle_vtep3,\
            port_handle_vtep5,port_handle_sw2,tgn1_sw2_intf1,tgn1_vtep8_intf1,tgn1_spine1_intf1,\
            port_handle_sw1,port_handle_sw2,port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5
  

        #port_handle = ConnectSpirent(labserver_ip,tgn_ip,[tgn1_sw1_intf1])
        #try:
        port_handle = ConnectSpirent(labserver_ip,tgn_ip,[tgn1_sw1_intf1,tgn1_sw2_intf1,tgn1_vtep1_intf1,tgn1_vtep2_intf1,tgn1_vtep3_intf1,tgn1_vtep4_intf1,tgn1_vtep5_intf1,tgn1_spine1_intf1])
        #except:
        #    log.info(banner("TGN CONNECT FAILED"))
        #    self.failed(goto=['common_cleanup']
        #tgn1_vtep3_intf2,tgn1_vtep1_intf2])
         
        port_handle_sw1 = port_handle[tgn1_sw1_intf1]
        port_handle_sw2 = port_handle[tgn1_sw2_intf1]
        #pdb.set_trace()
 
       
        #port_handle_sw2 = port_handle[tgn1_sw2_intf1]

        port_handle_vtep1 = port_handle[tgn1_vtep1_intf1]
        port_handle_vtep2 = port_handle[tgn1_vtep2_intf1]
        port_handle_vtep3 = port_handle[tgn1_vtep3_intf1]
        port_handle_vtep4 = port_handle[tgn1_vtep4_intf1]
        port_handle_vtep5 = port_handle[tgn1_vtep5_intf1]
        port_handle_spine1 = port_handle[tgn1_spine1_intf1]

        port_handle_list = [port_handle_sw1,port_handle_sw2,port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]
        #pdb.set_trace()
        
#################
  ######################################################
###                          TESTCASE BLOCK                         ###
#######################################################################
#
# Place your code that implements the test steps for the test case.
# Each test may or may not contains sections:
#           setup   - test preparation
#           test    - test action
#           cleanup - test wrap-up
 


class TC01_Nve_Simulation_To_Scale(aetest.Testcase):
    ###    This is de  scription for my testcase two

    @aetest.setup
    def setup(self):
        #log.info("Pass testcase setup")
        threads = []
        for uut in [spine1]:
            adv_nwk_list_tgn =[]
            neight_list_spine_tgn = []
            for intf in uut.interfaces.keys():
                if 'loopback1' in intf:
                    intf = uut.interfaces[intf].intf
                    bgp_rid=(str(uut.interfaces[intf].ipv4))[:-3]
                
                elif 'tgn' in intf:
                    intf_tgn = uut.interfaces[intf].intf
                    leaf_tgn_ip=str(uut.interfaces[intf].ipv4) 
                    leaf_neigh=leaf_tgn_ip.split('/')[0][:-1]+'0/8'
                    neight_list_spine_tgn.append(leaf_neigh)
                    adv_nwk_list_tgn.append(leaf_neigh)

            if 'yes' in vtep_emulation_spirent:
                spine_bgp_obj2=IbgpSpineNode(uut,bgp_rid,'65001',adv_nwk_list_tgn,neight_list_spine_tgn,intf_tgn,'ibgp-vxlan-tgn')
                t3 = threading.Thread(target= spine_bgp_obj2.bgp_conf)
                threads.append(t3)

        for t in threads: 
            t.start()
        for t in threads: 
            t.join(100)  
 
        log.info(banner("S T A R T I N G     vTEP     E M U L A T I O N "))
        log.info(" Configuration time depends on scale , Current Scale is %r",vtep_scale)

        start_time = time.time()


        scale = vtep_scale
        leaf_tgn_ip1 = leaf_tgn_ip.split('/')[0]
        bgp_host1_ip1 = leaf_tgn_ip.split('/')[0][:-1]+'2'

        bgp1 = sth.emulation_bgp_config (
                mode='enable',
                port_handle=port_handle_spine1,
                count=scale,
                active_connect_enable=1,
                ip_version=4,
                local_ip_addr=bgp_host1_ip1,
                netmask='8',
                remote_ip_addr=leaf_tgn_ip1,
                next_hop_ip=leaf_tgn_ip1,
                local_as=65001,
                local_router_id=bgp_host1_ip1,
                remote_as=65001,
                local_addr_step='0.0.0.1',
                retry_time=30,
                retries=10,
                routes_per_msg=20,
                hold_time=180,
                update_interval=45,
                ipv4_unicast_nlri=1,
                ipv4_e_vpn_nlri=1,
                graceful_restart_enable=1,
                restart_time=200)


 
        bgp_dev_list = []
        bgp_dev = 'emulateddevice'
        for i in range(1,(scale+1)):
            bgp_dev1 = bgp_dev+str(i)
            bgp_dev_list.append(bgp_dev1)
 

        ip = IPv4Address(bgp_host1_ip1)
        ip_list = []
        for i in range(0,scale):
            ip_list.append(ip)
            ip = ip + i


        mac = 'aa:bb:cc:dd:ee:01' 

 
        for router,ip in zip(bgp_dev_list,ip_list):
            type3 = sth.emulation_bgp_route_config (
                mode = 'add',
                handle = router,
                evpn_type3_agg_ip = str(ip),
                route_type = 'evpn_type3',
                evpn_type3_community='65001:1',
                evpn_type3_data_plane_encap='vxlan',
                evpn_type3_encap_label='201001',
                evpn_type3_origin='igp',
                evpn_type3_route_target='65001:201001',
                )
            type2 = sth.emulation_bgp_route_config (
                mode = 'add',
                handle = router,
                evpn_type2_mac_addr_start =mac,
                route_type = 'evpn_type2',
                evpn_type2_community='65001:1',
                evpn_type2_data_plane_encap ='vxlan',
                evpn_type2_encap_label='201001',
                evpn_type2_origin='igp',
                evpn_type2_route_target ='65001:201001',
                )


        bgp1_start1 = sth.emulation_bgp_control (
                handle = bgp_dev_list,
                mode = 'start')

        elapsed_time = time.time() - start_time
 
        log.info(banner("C O M P L E A T E D    vTEP   E M U L A T I O N  "))

        log.info("Thank you for the patience :-) , Time taken for Simulating %r vTEP's is %r",vtep_scale,elapsed_time)


        time.sleep(60)
        for uut in spine_uut_list:
            log.info("Checking bgp state @ %r",uut)
            test1 = leaf_protocol_check(uut,['bgp'])
            if not test1:
                self.failed()

        time.sleep(100)

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        log.info("Pass testcase cleanup")



 
     
 
    
class TC01_Nve_Peer_State_Verify(aetest.Testcase):
    ###    This is de  scription for my testcase two

    @aetest.setup
    def setup(self):
        log.info("Pass testcase setup")

        ArpTrafficGenerator2(port_handle_sw1,'1001','5.1.255.250','5.1.255.240','00a7.0001.0001',1,1)
        ArpTrafficGenerator2(port_handle_sw2,'1001','5.1.255.240','5.1.255.250','00a8.0002.0002',1,1)
        ArpTrafficGenerator2(port_handle_vtep5,'1001','5.1.255.230','5.1.255.250','00a6.0002.0002',1,1)

        for port_hdl in [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'run')
        countdown(5) 
 
    @aetest.test      
    def check_nve_peer_state(self):
        #for uut in vtep_uut_list:
        test1 = NvePeerLearning(port_handle_list,vlan_start,vtep_uut_list,3)
        if not test1:
            log.info(banner("NvePeerLearning F A I L E D"))
            self.failed(goto=['common_cleanup'])
   
    @aetest.cleanup
    def cleanup(self):
       for port_hdl in  port_handle_list:
          traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'stop', db_file=0 ) 
          traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'reset') 

 
class TC02_Nve_Vni_State_Verify(aetest.Testcase):
    ###    This is description for my testcase two

    @aetest.test
    def check_nve_vni_state(self):
        for uut in vtep_uut_list:
            uut.execute('terminal length 0')
            uut.execute('show spanning-tree')
            test1 = leaf_protocol_check222(uut,['nve-vni'])
            if not test1:
                self.failed(goto=['common_cleanup'])

    @aetest.cleanup
    def cleanup(self):
        pass
        """ testcase clean up """
 
class TC03_Vxlan_Consistency_check(aetest.Testcase):
    ###    This is description for my testcase two

    @aetest.setup
    def setup(self):
        log.info("Pass testcase setup")
 

    @aetest.test
    def vxlan_consistency_check_all(self):
        for uut in vpc_uut_list:
            check = uut.execute('show consistency-checke vxlan vlan all')
            if not 'Consistency Check: PASSED' in check:
                self.failed()

    @aetest.test
    def vxlan_consistency_check_vlan(self):
        for uut in vpc_uut_list:
            check = uut.execute('show consistency-checke vxlan vlan {vlan}'.format(vlan=vlan_start+1))
            if not 'Consistency Check: PASSED' in check:
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 
  
class TC04_Broadcast_Traffic(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):

        #log.info(banner("-------triggering peer Learning------"))
     
        ArpTrafficGenerator2(port_handle_sw1,'1001','5.1.255.250','5.1.255.240','00a7.0001.0001',1,1)
        ArpTrafficGenerator2(port_handle_sw2,'1001','5.1.255.240','5.1.255.250','00a8.0002.0002',1,1)
        ArpTrafficGenerator2(port_handle_vtep5,'1001','5.1.255.230','5.1.255.250','00a6.0002.0002',1,1)

        for port_hdl in [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'run')
        countdown(5) 
        


 
        test1 = NvePeerLearning(port_handle_list,vlan_start,vtep_uut_list,3)
        if not test1:
            log.info(banner("NvePeerLearning F A I L E D"))

            for port_hdl in  [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
                sth.traffic_control (port_handle = port_hdl, action = 'stop', db_file=0 )

            self.failed(goto=['TC39_KUC_Traffic'])
 

        #for port_hdl in  [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
        #   sth.traffic_control (port_handle = port_hdl, action = 'stop', db_file=0 )


        log.info("Generating hosts and flood traffic") 
        ip_sa1=str(ip_address(find_svi_ip222(vtep1,vlan_start))+1) 
        ip_sa2=str(ip_address(ip_sa1)+100) 


        test1= FloodTrafficGeneratorScale(port_handle_sw1,vlan_start,ip_sa1,'100.100.100.100',rate,str(vlan_vni_scale))
        if not test1:
            log.info(banner(" test1 Failed"))
            self.failed(goto=['TC39_KUC_Traffic'])

        test2= FloodTrafficGeneratorScale(port_handle_sw2,vlan_start,ip_sa2,'200.200.200.200',rate,str(vlan_vni_scale))
        if not test2:
            log.info(banner(" test2 Failed"))
            self.failed(goto=['TC39_KUC_Traffic'])

        for port_hdl in  [port_handle_sw1,port_handle_sw2]:
            sth.traffic_control (port_handle = port_hdl, action = 'stop', db_file=0 )
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'run')
            log.info("Traffic starting for port %r",port_hdl) 

        log.info(banner("Counting 120 seconds before checking rate"))
       
        countdown(120)

    @aetest.test
    def TrafficTestBroadcast(self):
        log.info(banner("Starting TriggerBgpProcRestart for Broadcast Encap Traffic"))  
          
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['TC39_KUC_Traffic'])

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC39_KUC_Traffic'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 
 
class TC05_Broadcast_Triggers1_bgp_restart_vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    @aetest.test
    def Trigger1BgpProcRestart(self):
        log.info(banner("Starting TriggerBgpProcRestart for Broadcast Encap Traffic"))     
             
        for uut in vpc_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'bgp')
        countdown(20)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 

class TC06_Broadcast_Triggers1_bgp_restart_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])


        #log.info(banner("-------triggering peer Learning------"))    
    @aetest.test
    def Trigger1BgpProcRestart(self):
        log.info(banner("Starting TriggerBgpProcRestart for Broadcast Encap Traffic"))     

 
        for uut in esi_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'bgp')
        countdown(20)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
  
 
class TC07_Broadcast_Triggers1_nve_restart_vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

 
    
    @aetest.test
    def Trigger2NveProcRestart(self, testscript, testbed):
        log.info(banner("Starting TriggerNveProcRestart for Broadcast Encap Traffic"))     

 

        for uut in vpc_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'nve')


        countdown(30)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
   

class TC08_Broadcast_Triggers1_nve_restart_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

 
 
    
    @aetest.test
    def Trigger2NveProcRestart(self, testscript, testbed):
        log.info(banner("Starting TriggerNveProcRestart for Broadcast Encap Traffic"))     
 
        for uut in esi_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'nve')


        countdown(30)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
   




 
class TC09_Broadcast_Triggers1_VlanAddRemovePort_Vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

     
    
    @aetest.test
    def Trigger3VlanAddRemovePort(self, testscript, testbed):

 

        log.info(banner("Starting Trigger1VlanAddRemove @ 5")) 
        for uut in [vtep1,vtep2]:
            if not TriggerVlanRemoveAddFromPort(uut,'Po101',vlan_range,3):
                log.info("TriggerPortVlanRemoveAdd failed @ 2")
                self.failed()

        countdown(120)
        #rate,int(pps)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed @ 1111"))
            #log.info("SLEEPING ANOTHER 60 SECs")
            #countdown(60)
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']  
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic received at a port %r is not @ expected rate',port_hdl)
                self.failed()
         
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    
 

class TC10_Broadcast_Triggers1_VlanAddRemovePort_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

         
    @aetest.test
    def Trigger3VlanAddRemovePort(self, testscript, testbed):
        log.info(banner("Starting Trigger1VlanAddRemove @ 5")) 
        for uut in [vtep3,vtep4]:
            if not TriggerVlanRemoveAddFromPort(uut,'Po101',vlan_range,3):
                log.info("TriggerPortVlanRemoveAdd failed @ 2")
                self.failed()
                countdown(120)
        countdown(120)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed @ 1111"))
            #log.info("SLEEPING ANOTHER 60 SECs")
            #countdown(60)
            self.failed()
            countdown(60)
        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']  
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic received at a port %r is not @ expected rate',port_hdl)
                self.failed()
                countdown(60)
         
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC11_Broadcast_Triggers_VPC_flap(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    
    @aetest.test
    def Trigger4AccessPortFlap(self, testscript, testbed):
        log.info(banner("Starting Trigger2PortFlap @ 8"))          
 
        for uut in [vtep1,vtep2]:
            if not TriggerPortFlap(uut,'po101',3):
                log.info("TriggerPortFlap failed @ 4")
                self.failed()
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass

 
  
class TC12_Broadcast_Triggers_ESI_flap(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    
    @aetest.test
    def Trigger4AccessPortFlap(self, testscript, testbed):
        log.info(banner("Starting Trigger2PortFlap @ 8"))          

 

        for uut in [vtep3,vtep4]:
            if not TriggerPortFlap(uut,'po101',3):
                log.info("TriggerPortFlap failed @ 4")
                self.failed()
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC13_Broadcast_Triggers_VPC_Core_flap(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
    @aetest.test
    def Trigger5CoreIfFlap(self, testscript, testbed):
        log.info(banner("Starting TriggerCoreIfFlap222 @ 8"))          

 
        if not TriggerCoreIfFlap222(vpc_uut_list): 
            log.info("TriggerCoreIfFlap222 failed @ 4")
            self.failed()
    
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    
 
 
class TC14_Broadcast_Triggers_ESI_Core_flap(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         

 
    @aetest.test
    def Trigger5CoreIfFlap(self, testscript, testbed):
        log.info(banner("Starting TriggerCoreIfFlap222 @ 8"))          
 
                    
        #for uut in vtep_uut_list:
        if not TriggerCoreIfFlap222(esi_uut_list): 
            log.info("TriggerCoreIfFlap222 failed @ 4")
            self.failed()
    
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 


class TC15_Broadcast_Triggers_VPC_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC16_Broadcast_Triggers_ESI_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC17_Broadcast_Triggers_VPC_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     


        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass

 
class TC18_Broadcast_Triggers_ESI_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     


        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


 
 

class TC19_Broadcast_Triggers_VPC_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC20_Broadcast_Triggers_ESI_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     


        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass




class TC21_Broadcast_Triggers_VPC_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC22_Broadcast_Triggers_ESI_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass





class TC23_Broadcast_Triggers_VPC_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC24_Broadcast_Triggers_ESI_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     


        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC25_Broadcast_Triggers_Spine_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass

        
class TC26_Broadcast_Triggers_Spine_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     


        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
         
class TC27_Broadcast_Triggers_Spine_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    
class TC28_Broadcast_Triggers_Spine_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
class TC29_Broadcast_Triggers_Spine_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     


        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        

class TC30_Broadcast_Triggers_VPC_Clear_ARP_MAC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



 
    @aetest.test
    def Trigger11ClearArpMac(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     


        for uut in vpc_uut_list:
            for i in range(1,5):
                uut.execute("clear ip arp vrf all")
                uut.execute("clear mac add dy")                              

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        


class TC31_Broadcast_Triggers_ESI_Clear_ARP_MAC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
 
    @aetest.test
    def Trigger11ClearArpMac(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     


        for uut in esi_uut_list:
            for i in range(1,5):
                uut.execute("clear ip arp vrf all")
                uut.execute("clear mac add dy")                              

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        




class TC32_Broadcast_Triggers_VPC_nve_Bounce(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
 
  
    @aetest.test
    def Trigger12NveShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        for uut in vpc_uut_list:
            cmd1 = \
                """
                interface nve 1
                shut
                """
            uut.configure(cmd1)
        countdown(5)                  
        for uut in vpc_uut_list:
            cmd2 = \
                """
                interface nve 1
                no shut
                """
            uut.configure(cmd2)

        countdown(60)


        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
        

class TC33_Broadcast_Triggers_ESI_nve_Bounce(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
  
    @aetest.test
    def Trigger12NveShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     


        for uut in esi_uut_list:
            cmd1 = \
                """
                interface nve 1
                shut
                """
            uut.configure(cmd1)
        countdown(5)                  
        for uut in esi_uut_list:
            cmd2 = \
                """
                interface nve 1
                no shut
                """
            uut.configure(cmd2)

        countdown(120)


        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
                

class TC34_Broadcast_Triggers_VLAN_Bounce_VPC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    




 
    @aetest.test
    def Trigger15VlanShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        for uut in vpc_uut_list:
            vlanshut = \
            """
            vlan {vlan_range}
            shut
            end
            """
            uut.configure(vlanshut.format(vlan_range=vlan_range))  
        countdown(5)
        for uut in vpc_uut_list:
            vlannoshut = \
            """
            vlan {vlan_range}
            no shut
            end
            """
            uut.configure(vlannoshut.format(vlan_range=vlan_range))                        

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
              

class TC35_Broadcast_Triggers_VLAN_Bounce_ESI(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    




 
    @aetest.test
    def Trigger15VlanShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        for uut in esi_uut_list:
            vlanshut = \
            """
            vlan {vlan_range}
            shut
            end
            """
            uut.configure(vlanshut.format(vlan_range=vlan_range))  
        countdown(5)
        for uut in esi_uut_list:
            vlannoshut = \
            """
            vlan {vlan_range}
            no shut
            end
            """
            uut.configure(vlannoshut.format(vlan_range=vlan_range))                        

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
                

class TC36_Broadcast_Triggers_VPC_Z_Flow1(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
 
 
    @aetest.test
    def Trigger13Zflow1(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep1.interfaces.keys():
            if 'vpc_po' in vtep1.interfaces[intf].type:
                vpc5 = vtep1.interfaces[intf].intf
                vtep1.configure(poshut.format(po=vpc5)) 

        for intf in vtep2.interfaces.keys():
            if 'l3_po' in vtep2.interfaces[intf].type:
                l3po6 = vtep2.interfaces[intf].intf
                vtep2.configure(poshut.format(po=l3po6)) 


 
        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep1.configure(ponoshut.format(po=vpc5)) 
            vtep2.configure(ponoshut.format(po=l3po6))
            countdown(60)
            self.failed() 

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


        vtep1.configure(ponoshut.format(po=vpc5)) 
        vtep2.configure(ponoshut.format(po=l3po6))

        countdown(100)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()
 

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """

        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep1.interfaces.keys():
            if 'vpc_po' in vtep1.interfaces[intf].type:
                vpc5 = vtep1.interfaces[intf].intf
                vtep1.configure(ponoshut.format(po=vpc5)) 

        for intf in vtep2.interfaces.keys():
            if 'l3_po' in vtep2.interfaces[intf].type:
                l3po6 = vtep2.interfaces[intf].intf
                vtep2.configure(ponoshut.format(po=l3po6)) 

 
class TC37_Broadcast_Triggers_VPC_Z_Flow2(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
     

    @aetest.test
    def Trigger14Zflow2(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep2.interfaces.keys():
            if 'vpc_po' in vtep2.interfaces[intf].type:
                vpc6 = vtep2.interfaces[intf].intf
                vtep2.configure(poshut.format(po=vpc6)) 

        for intf in vtep1.interfaces.keys():
            if 'l3_po' in vtep1.interfaces[intf].type:
                l3po5 = vtep1.interfaces[intf].intf
                vtep1.configure(poshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep2.configure(ponoshut.format(po=vpc6))  
            vtep1.configure(ponoshut.format(po=l3po5))
            countdown(60)
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()


        vtep2.configure(ponoshut.format(po=vpc6))  
        vtep1.configure(ponoshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()
        
        countdown(120) 
    
    @aetest.cleanup
    def cleanup(self):
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep2.interfaces.keys():
            if 'vpc_po' in vtep2.interfaces[intf].type:
                vpc6 = vtep2.interfaces[intf].intf
                vtep2.configure(ponoshut.format(po=vpc6)) 

        for intf in vtep1.interfaces.keys():
            if 'l3_po' in vtep1.interfaces[intf].type:
                l3po5 = vtep1.interfaces[intf].intf
                vtep1.configure(ponoshut.format(po=l3po5))
       
       
 
class TC38_Broadcast_Triggers_ESI_Failover(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
     

    @aetest.test
    def TriggerESIFailover(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep3.interfaces.keys():
            if 'esi_po' in vtep3.interfaces[intf].type:
                esi = vtep3.interfaces[intf].intf
                vtep3.configure(poshut.format(po=esi)) 

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep3.configure(ponoshut.format(po=esi))  
            #vtep1.configure(ponoshut.format(po=l3po5))
            countdown(60)
            self.failed()

        vtep3.configure(ponoshut.format(po=esi))  


        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()
        
        countdown(120) 
    
    @aetest.cleanup
    def cleanup(self):

        ponoshut = \
            """
            interface po{po}
            no shut
            """


        for intf in vtep3.interfaces.keys():
            if 'esi_po' in vtep3.interfaces[intf].type:
                esi = vtep3.interfaces[intf].intf
                vtep3.configure(poshut.format(po=esi)) 



 
 
class TC39_KUC_Traffic(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):

        log.info(banner("-------D E L E T I N G   P R E V  S T R E A M S------"))

        for port_hdl in  port_handle_list:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'stop', db_file=0 ) 
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'reset') 

     
        ArpTrafficGenerator2(port_handle_sw1,'1001','5.1.255.250','5.1.255.240','00a7.0001.0001',1,1)
        ArpTrafficGenerator2(port_handle_sw2,'1001','5.1.255.240','5.1.255.250','00a8.0002.0002',1,1)
        ArpTrafficGenerator2(port_handle_vtep5,'1001','5.1.255.230','5.1.255.250','00a6.0002.0002',1,1)

        for port_hdl in [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'run')

        countdown(5) 

 
        test1 = NvePeerLearning(port_handle_list,vlan_start,vtep_uut_list,3)
        if not test1:
            log.info(banner("NvePeerLearning F A I L E D"))
            for port_hdl in  [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
                sth.traffic_control (port_handle = port_hdl, action = 'stop', db_file=0 )
            self.failed(goto=['TC74_Routed_triggers'])
 
        for port_hdl in  port_handle_list:
            log.info(banner("Deleting All streams"))
            sth.traffic_control(port_handle = port_hdl, action = 'reset')

        log.info("Generating hosts and flood traffic") 
        ip_sa1=str(ip_address(find_svi_ip222(vtep1,vlan_start))+1) 
        ip_sa2=str(ip_address(ip_sa1)+100) 


        SpirentBidirStream222(port_hdl1=port_handle_sw1,port_hdl2=port_handle_sw2,vlan1=vlan_start,vlan2=vlan_start,\
        scale=vlan_vni_scale,ip1=ip_sa1,ip2=ip_sa2,gw1=ip_sa2,gw2=ip_sa1,rate_pps=rate)

        for uut in vtep_uut_list:
            for i in range(1,2):
                uut.execute('clear mac address-table dynamic')
                uut.execute('clear ip arp vrf all')
        
        countdown(30)

        for port_hdl in [port_handle_sw1,port_handle_sw2]:
            doarp = sth.arp_control(port_handle=port_hdl,arp_target='allstream',arpnd_report_retrieve='1')

        doarp = sth.arp_control(arp_target='allstream',arpnd_report_retrieve='1')
        #sth.arp_control(port_handle=port_handle_sw2,arp_target='allstream',arpnd_report_retrieve='1')

        for port_hdl in [port_handle_sw1,port_handle_sw2]:
            log.info(banner("------S T A R T I N G    A R P----"))
            #doarp = sth.arp_control(arp_target='allstream',arpnd_report_retrieve='1')
            for i in range(1,2):
                log.info('ARPing for %r th time',i)
            doarp = sth.arp_control(port_handle=port_hdl,arp_target='allstream',arpnd_report_retrieve='1',\
                arp_cache_retrieve='1')
            if not 'SUCCESSFUL' in doarp['arpnd_report'][port_hdl]['arpnd_status']:
                log.info("ARP Fail @ TC10 Setup,arpnd_satus Failed for potrt %r",port_hdl)
                cache = doarp[port_hdl]
                log.info("++++++++++++++++++++++")
                log.info("cache %r",cache)
                log.info("++++++++++++++++++++++")
                for uut in [vtep1,vtep2,vtep3,vtep4]:                    
                    count = uut.execute('show ip arp vrf all | incl Vlan | count')
                    if int(count) < int(vlan_vni_scale):
                        log.info('ARP entries fail @ %r',uut)
                        op=uut.execute('show ip arp vrf all')
                        log.info('ARP at @ %r is %r',uut,op)
                        #self.failed(goto=['cleanup'])
                #self.failed(goto=['cleanup'])
            else:
                log.info("arpnd_status PASSED at TC10 for potrt %r",port_hdl)


    
        for i in range(1,4):
            countdown(2)
            doarp1 = sth.arp_control(port_handle=port_handle_sw1,arp_target='allstream',arpnd_report_retrieve='1')
            doarp2 = sth.arp_control(port_handle=port_handle_sw2,arp_target='allstream',arpnd_report_retrieve='1')


        if not 'SUCCESSFUL' in doarp1['arpnd_report'][port_handle_sw1]['arpnd_status']:
            log.info("ARP Fail @ TC10 Setup,arpnd_status Failed for potrt %r",port_handle_sw1)
            self.failed(goto=['TC74_Routed_triggers'])
        else:
            log.info("arpnd_status PASSED at TC10 for potrt %r",port_handle_sw1)

        if not 'SUCCESSFUL' in doarp2['arpnd_report'][port_handle_sw2]['arpnd_status']:
            log.info("ARP Fail @ TC10 Setup,arpnd_status Failed for potrt %r",port_handle_sw2)
            self.failed(goto=['TC74_Routed_triggers'])
        else:
            log.info("arpnd_status PASSED at TC10 for potrt %r",port_handle_sw2)
                    

        for port_hdl in port_handle_list:
            sth.traffic_control(port_handle = port_hdl, action = 'clear_stats')
            sth.traffic_control (port_handle = port_hdl, action = 'stop', db_file=0 )
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'run')
            log.info("Traffic starting for port %r",port_hdl) 

        log.info(banner("Counting 120 seconds before checking rate"))
       
        countdown(120)
  
    @aetest.test
    def TrafficTestKUC(self):

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['TC74_Routed_triggers'])

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC74_Routed_triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 

class TC40_KUC_Triggers1_bgp_restart_vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    @aetest.test
    def Trigger1BgpProcRestart(self):
        log.info(banner("Starting TriggerBgpProcRestart for Broadcast Encap Traffic"))     
             
        for uut in vpc_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'bgp')
        countdown(20)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 
class TC41_KUC_Triggers1_bgp_restart_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])


        #log.info(banner("-------triggering peer Learning------"))    
    @aetest.test
    def Trigger1BgpProcRestart(self):
        log.info(banner("Starting TriggerBgpProcRestart for Broadcast Encap Traffic"))     

 
        for uut in esi_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'bgp')
        countdown(20)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
  
 
class TC42_KUC_Triggers1_nve_restart_vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    @aetest.test
    def Trigger2NveProcRestart(self, testscript, testbed):
        log.info(banner("Starting TriggerNveProcRestart for Broadcast Encap Traffic"))     

 

        for uut in vpc_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'nve')


        countdown(30)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
   

class TC43_KUC_Triggers1_nve_restart_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

 
 
    
    @aetest.test
    def Trigger2NveProcRestart(self, testscript, testbed):
        log.info(banner("Starting TriggerNveProcRestart for Broadcast Encap Traffic"))     
 

        for uut in esi_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'nve')


        countdown(30)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
   




 
class TC44_KUC_Triggers1_VlanAddRemovePort_Vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

     
    
    @aetest.test
    def Trigger3VlanAddRemovePort(self, testscript, testbed):

  
        log.info(banner("Starting Trigger1VlanAddRemove @ 5")) 
        for uut in [vtep1,vtep2]:
            if not TriggerVlanRemoveAddFromPort(uut,'Po101',vlan_range,3):
                log.info("TriggerPortVlanRemoveAdd failed @ 2")
                self.failed()

        countdown(120)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed @ 1111"))
            #log.info("SLEEPING ANOTHER 60 SECs")
            #countdown(60)
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']  
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic received at a port %r is not @ expected rate',port_hdl)
                self.failed()
         
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC45_KUC_Triggers1_VlanAddRemovePort_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

         
    @aetest.test
    def Trigger3VlanAddRemovePort(self, testscript, testbed):

 
        log.info(banner("Starting Trigger1VlanAddRemove @ 5")) 
        for uut in [vtep3,vtep4]:
            if not TriggerVlanRemoveAddFromPort(uut,'Po101',vlan_range,3):
                log.info("TriggerPortVlanRemoveAdd failed @ 2")
                self.failed()

        countdown(120)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed @ 1111"))
            #log.info("SLEEPING ANOTHER 60 SECs")
            #countdown(60)
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']  
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic received at a port %r is not @ expected rate',port_hdl)
                self.failed()
         
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC46_KUC_Triggers_VPC_flap(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    
    @aetest.test
    def Trigger4AccessPortFlap(self, testscript, testbed):
        log.info(banner("Starting Trigger2PortFlap @ 8"))          

                     

        for uut in [vtep1,vtep2]:
            if not TriggerPortFlap(uut,'po101',3):
                log.info("TriggerPortFlap failed @ 4")
                self.failed()
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
  
class TC47_KUC_Triggers_ESI_flap(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    
    @aetest.test
    def Trigger4AccessPortFlap(self, testscript, testbed):
        log.info(banner("Starting Trigger2PortFlap @ 8"))          
    

        for uut in [vtep3,vtep4]:
            if not TriggerPortFlap(uut,'po101',3):
                log.info("TriggerPortFlap failed @ 4")
                self.failed()
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC48_KUC_Triggers_VPC_Core_flap(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         

 
    @aetest.test
    def Trigger5CoreIfFlap(self, testscript, testbed):
        log.info(banner("Starting TriggerCoreIfFlap222 @ 8"))          
 
        #for uut in vtep_uut_list:
        if not TriggerCoreIfFlap222(vpc_uut_list): 
            log.info("TriggerCoreIfFlap222 failed @ 4")
            self.failed()
    
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC49_KUC_Triggers_ESI_Core_flap(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         

 
    @aetest.test
    def Trigger5CoreIfFlap(self, testscript, testbed):
        log.info(banner("Starting TriggerCoreIfFlap222 @ 8"))          

               
        #for uut in vtep_uut_list:
        if not TriggerCoreIfFlap222(esi_uut_list): 
            log.info("TriggerCoreIfFlap222 failed @ 4")
            self.failed()
    
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC50_KUC_Triggers_VPC_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC51_KUC_Triggers_ESI_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC52_KUC_Triggers_VPC_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     

 
        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC53_KUC_Triggers_ESI_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     

 
        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


 

 

class TC54_KUC_Triggers_VPC_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

             

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC55_KUC_Triggers_ESI_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

  

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass




class TC56_KUC_Triggers_VPC_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC57_KUC_Triggers_ESI_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass





class TC58_KUC_Triggers_VPC_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     
 

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC59_KUC_Triggers_ESI_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC60_KUC_Triggers_Spine_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass

        
class TC61_KUC_Triggers_Spine_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     

 

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
         
class TC62_KUC_Triggers_Spine_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

   

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(150)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    
class TC63_KUC_Triggers_Spine_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
class TC64_KUC_Triggers_Spine_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 
        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        

class TC65_KUC_Triggers_VPC_Clear_ARP_MAC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
 
    @aetest.test
    def Trigger11ClearArpMac(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

         

        for uut in vpc_uut_list:
            for i in range(1,5):
                uut.execute("clear ip arp vrf all")
                uut.execute("clear mac add dy")                              

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        


class TC66_KUC_Triggers_ESI_Clear_ARP_MAC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



 
    @aetest.test
    def Trigger11ClearArpMac(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

  

        for uut in esi_uut_list:
            for i in range(1,5):
                uut.execute("clear ip arp vrf all")
                uut.execute("clear mac add dy")                              

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        




class TC67_KUC_Triggers_VPC_nve_Bounce(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



  
    @aetest.test
    def Trigger12NveShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

  

        for uut in vpc_uut_list:
            cmd1 = \
                """
                interface nve 1
                shut
                """
            uut.configure(cmd1)
        countdown(5)                  
        for uut in vpc_uut_list:
            cmd2 = \
                """
                interface nve 1
                no shut
                """
            uut.configure(cmd2)

        countdown(60)


        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
        

class TC68_KUC_Triggers_ESI_nve_Bounce(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



  
    @aetest.test
    def Trigger12NveShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in esi_uut_list:
            cmd1 = \
                """
                interface nve 1
                shut
                """
            uut.configure(cmd1)
        countdown(5)                  
        for uut in esi_uut_list:
            cmd2 = \
                """
                interface nve 1
                no shut
                """
            uut.configure(cmd2)

        countdown(60)


        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
        



        

class TC69_KUC_Triggers_VLAN_Bounce_VPC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    




 
    @aetest.test
    def Trigger15VlanShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in vpc_uut_list:
            vlanshut = \
            """
            vlan {vlan_range}
            shut
            end
            """
            uut.configure(vlanshut.format(vlan_range=vlan_range))  
        countdown(5)
        for uut in vpc_uut_list:
            vlannoshut = \
            """
            vlan {vlan_range}
            no shut
            end
            """
            uut.configure(vlannoshut.format(vlan_range=vlan_range))                        

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        


        

class TC70_KUC_Triggers_VLAN_Bounce_ESI(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    




 
    @aetest.test
    def Trigger15VlanShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     
 
        for uut in esi_uut_list:
            vlanshut = \
            """
            vlan {vlan_range}
            shut
            end
            """
            uut.configure(vlanshut.format(vlan_range=vlan_range))  
        countdown(5)
        for uut in esi_uut_list:
            vlannoshut = \
            """
            vlan {vlan_range}
            no shut
            end
            """
            uut.configure(vlannoshut.format(vlan_range=vlan_range))                        

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
                

class TC71_KUC_Triggers_VPC_Z_Flow1(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
 
 
    @aetest.test
    def Trigger13Zflow1(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep1.interfaces.keys():
            if 'vpc_po' in vtep1.interfaces[intf].type:
                vpc5 = vtep1.interfaces[intf].intf
                vtep1.configure(poshut.format(po=vpc5)) 

        for intf in vtep2.interfaces.keys():
            if 'l3_po' in vtep2.interfaces[intf].type:
                l3po6 = vtep2.interfaces[intf].intf
                vtep2.configure(poshut.format(po=l3po6)) 


 
        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep1.configure(ponoshut.format(po=vpc5)) 
            vtep2.configure(ponoshut.format(po=l3po6))
            countdown(60)
            self.failed() 

        vtep1.configure(ponoshut.format(po=vpc5)) 
        vtep2.configure(ponoshut.format(po=l3po6))

        countdown(100)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
 




    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """

        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep1.interfaces.keys():
            if 'vpc_po' in vtep1.interfaces[intf].type:
                vpc5 = vtep1.interfaces[intf].intf
                vtep1.configure(ponoshut.format(po=vpc5)) 

        for intf in vtep2.interfaces.keys():
            if 'l3_po' in vtep2.interfaces[intf].type:
                l3po6 = vtep2.interfaces[intf].intf
                vtep2.configure(ponoshut.format(po=l3po6)) 

 
class TC72_KUC_Triggers_VPC_Z_Flow2(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
     

    @aetest.test
    def Trigger14Zflow2(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep2.interfaces.keys():
            if 'vpc_po' in vtep2.interfaces[intf].type:
                vpc6 = vtep2.interfaces[intf].intf
                vtep2.configure(poshut.format(po=vpc6)) 

        for intf in vtep1.interfaces.keys():
            if 'l3_po' in vtep1.interfaces[intf].type:
                l3po5 = vtep1.interfaces[intf].intf
                vtep1.configure(poshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep2.configure(ponoshut.format(po=vpc6))  
            vtep1.configure(ponoshut.format(po=l3po5))
            countdown(60)
            self.failed()

        vtep2.configure(ponoshut.format(po=vpc6))  
        vtep1.configure(ponoshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
        
        countdown(120) 
    
    @aetest.cleanup
    def cleanup(self):


        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep2.interfaces.keys():
            if 'vpc_po' in vtep2.interfaces[intf].type:
                vpc6 = vtep2.interfaces[intf].intf
                vtep2.configure(ponoshut.format(po=vpc6)) 

        for intf in vtep1.interfaces.keys():
            if 'l3_po' in vtep1.interfaces[intf].type:
                l3po5 = vtep1.interfaces[intf].intf
                vtep1.configure(ponoshut.format(po=l3po5))
       
       
 
 
class TC73_KUC_Triggers_ESI_Failover(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
     

    @aetest.test
    def TriggerESIFailover(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep3.interfaces.keys():
            if 'esi_po' in vtep3.interfaces[intf].type:
                esi = vtep3.interfaces[intf].intf
                vtep3.configure(poshut.format(po=esi)) 

        #for intf in vtep1.interfaces.keys():
        #    if 'l3_po' in vtep1.interfaces[intf].type:
        #        l3po5 = vtep1.interfaces[intf].intf
        #        vtep1.configure(poshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep3.configure(ponoshut.format(po=esi))  
            #vtep1.configure(ponoshut.format(po=l3po5))
            countdown(60)
            self.failed()

        vtep3.configure(ponoshut.format(po=esi))  
        #vtep1.configure(ponoshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
        
        countdown(120) 
    
    @aetest.cleanup
    def cleanup(self):

        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep3.interfaces.keys():
            if 'esi_po' in vtep2.interfaces[intf].type:
                esi = vtep2.interfaces[intf].intf
                vtep3.configure(poshut.format(po=esi)) 

       

  
class TC74_Routed_triggers(aetest.Testcase):

  
    @aetest.setup
    def setup(self):
        log.info(banner("-------Deleting All Streams------"))

        for port_hdl in  port_handle_list:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'stop', db_file=0 ) 
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'reset') 

  

        ArpTrafficGenerator2(port_handle_sw1,'1001','5.1.255.250','5.1.0.1','00a7.0001.0001',1,1)
        ArpTrafficGenerator2(port_handle_sw2,'1001','5.1.255.240','5.1.0.1','00a8.0002.0002',1,1)
        ArpTrafficGenerator2(port_handle_vtep5,'1001','5.1.255.230','5.1.0.1','00a6.0002.0002',1,1)

        for port_hdl in [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'run')

        countdown(5) 

 
        test1 = NvePeerLearning(port_handle_list,vlan_start,vtep_uut_list,3)
        if not test1:
            log.info(banner("NvePeerLearning F A I L E D"))

            for port_hdl in  [port_handle_sw1,port_handle_sw2,port_handle_vtep5]:
                sth.traffic_control (port_handle = port_hdl, action = 'stop', db_file=0 )

            self.failed(goto=['common_cleanup'])

        stream_scale = int(vlan_vni_scale/2)
        op = vtep1.execute('show vrf all | incl vxlan')
        op1 = op.splitlines()
        vrf_list=[]
        for line in op1:
            if line:
                if 'own' in line:
                    self.failed()
                else:
                    vrf = line.split()[0]
                    vrf_list.append(vrf)
    

        for vrf in vrf_list:
            op = vtep1.execute('show ip int brief vrf {vrf}'.format(vrf=vrf))
            op1 = op.splitlines()
            vlan_list = []
            ip_list = []
            for line in op1:
                if line:
                    if 'Vlan' in line:
                        vlan_list.append(line.split()[0].replace("Vlan",""))
                        ip_list.append(line.split()[1])
         
            if not len(vlan_list) == len(ip_list):
                self.failed(goto=['common_cleanup'])
            else:            
                gw1 = str(ip_address(ip_list[0]))
                ip1 = str(ip_address(gw1)+1)
                ip11= str(ip_address(ip1)+100)

                #ScaleSpirentHostBidirStream(port_handle_sw1,port_handle_sw2,vlan_list[0],vlan_list[0],ip1,ip11,gw1,gw1,str(pps),10)
             
 
                SpirentHostBidirStream(port_handle_sw1,port_handle_sw2,vlan_list[0],vlan_list[0],ip1,ip11,gw1,gw1,str(pps))
   
                for i in range(1,len(vlan_list)):
                    vlan2 = vlan_list[i]
                    gw2 = ip_list[i]  
                    ip2 = str(ip_address(gw2)+100) 
                    SpirentHostBidirStream(port_handle_sw1,port_handle_sw2,vlan_list[0],vlan2,ip1,ip2,gw1,gw2,str(pps))
    
     
        for port_hdl in [port_handle_sw1,port_handle_sw2]:
            log.info(banner("------S T A R T I N G    A R P----"))
            #doarp = sth.arp_control(arp_target='allstream',arpnd_report_retrieve='1')
            for i in range(1,3):
                doarp = sth.arp_control(port_handle=port_hdl,arp_target='allstream',arpnd_report_retrieve='1')

            if not 'SUCCESSFUL' in doarp['arpnd_report'][port_hdl]['arpnd_status']:
                log.info("arpnd_status Failed for potrt %r",port_hdl)
                self.failed(goto=['common_cleanup'])
            else:
                log.info("arpnd_status PASSED for potrt %r",port_hdl)


        for port_hdl in port_handle_list:
            sth.traffic_control(port_handle = port_hdl, action = 'clear_stats')
            sth.traffic_control (port_handle = port_hdl, action = 'stop', db_file=0 )
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'run')
            log.info("Traffic starting for port %r",port_hdl) 
   
        log.info(banner("Counting 120 seconds before checking rate"))
       
        countdown(60)

    @aetest.test
    def TrafficTestRouted(self):  
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,tol)
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['common_cleanup'])

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+-- RX rate at Port %r is : %r --+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if int(rx_rate) > int(pps):
                log.info('TRAFFIC is FLOODed for Some VLANS')
                self.failed(goto=['common_cleanup'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 

class TC75_Routed_Triggers1_bgp_restart_vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    @aetest.test
    def Trigger1BgpProcRestart(self):
        log.info(banner("Starting TriggerBgpProcRestart for Broadcast Encap Traffic"))     
             
        for uut in vpc_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'bgp')
        countdown(20)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
 
class TC76_Routed_Triggers1_bgp_restart_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])


        #log.info(banner("-------triggering peer Learning------"))    
    @aetest.test
    def Trigger1BgpProcRestart(self):
        log.info(banner("Starting TriggerBgpProcRestart for Broadcast Encap Traffic"))     

 
        for uut in esi_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'bgp')
        countdown(20)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed()

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
  
 
class TC77_Routed_Triggers1_nve_restart_vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

 
    
    @aetest.test
    def Trigger2NveProcRestart(self, testscript, testbed):
        log.info(banner("Starting TriggerNveProcRestart for Broadcast Encap Traffic"))     

 

        for uut in vpc_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'nve')


        countdown(30)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
   

class TC78_Routed_Triggers1_nve_restart_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

 
 
    
    @aetest.test
    def Trigger2NveProcRestart(self, testscript, testbed):
        log.info(banner("Starting TriggerNveProcRestart for Broadcast Encap Traffic"))     

 
        for uut in esi_uut_list:
            for i in range(1,2):
                pass
                #ProcessRestart2(uut,'nve')


        countdown(30)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
   




 
class TC79_Routed_Triggers1_VlanAddRemovePort_Vpc(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

     
    
    @aetest.test
    def Trigger3VlanAddRemovePort(self, testscript, testbed):


 


        log.info(banner("Starting Trigger1VlanAddRemove @ 5")) 
        for uut in [vtep1,vtep2]:
            if not TriggerVlanRemoveAddFromPort(uut,'Po101',vlan_range,3):
                log.info("TriggerPortVlanRemoveAdd failed @ 2")
                self.failed()

        countdown(120)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed @ 1111"))
            #log.info("SLEEPING ANOTHER 60 SECs")
            #countdown(60)
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']  
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic received at a port %r is not @ expected rate',port_hdl)
                self.failed()
         
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC80_Routed_Triggers1_VlanAddRemovePort_esi(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

         
    @aetest.test
    def Trigger3VlanAddRemovePort(self, testscript, testbed):


 
        log.info(banner("Starting Trigger1VlanAddRemove @ 5")) 
        for uut in [vtep3,vtep4]:
            if not TriggerVlanRemoveAddFromPort(uut,'Po101',vlan_range,3):
                log.info("TriggerPortVlanRemoveAdd failed @ 2")
                self.failed()

        countdown(120)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed @ 1111"))
            #log.info("SLEEPING ANOTHER 60 SECs")
            #countdown(60)
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']  
            if abs(int(rx_rate) - int(rate)*2) > int(pps):
                log.info('Traffic received at a port %r is not @ expected rate',port_hdl)
                self.failed()
         
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC81_Routed_Triggers_VPC_flap(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    
    @aetest.test
    def Trigger4AccessPortFlap(self, testscript, testbed):
        log.info(banner("Starting Trigger2PortFlap @ 8"))          

 

        for uut in [vtep1,vtep2]:
            if not TriggerPortFlap(uut,'po101',3):
                log.info("TriggerPortFlap failed @ 4")
                self.failed()
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
  
class TC82_Routed_Triggers_ESI_flap(aetest.Testcase):
    ###    This is description for my testcase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])

    
    @aetest.test
    def Trigger4AccessPortFlap(self, testscript, testbed):
        log.info(banner("Starting Trigger2PortFlap @ 8"))          

 

        for uut in [vtep3,vtep4]:
            if not TriggerPortFlap(uut,'po101',3):
                log.info("TriggerPortFlap failed @ 4")
                self.failed()
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC83_Routed_Triggers_VPC_Core_flap(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         

 
    @aetest.test
    def Trigger5CoreIfFlap(self, testscript, testbed):
        log.info(banner("Starting TriggerCoreIfFlap222 @ 8"))          

 

        #for uut in vtep_uut_list:
        if not TriggerCoreIfFlap222(vpc_uut_list): 
            log.info("TriggerCoreIfFlap222 failed @ 4")
            self.failed()
    
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    


class TC84_Routed_Triggers_ESI_Core_flap(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         

 
    @aetest.test
    def Trigger5CoreIfFlap(self, testscript, testbed):
        log.info(banner("Starting TriggerCoreIfFlap222 @ 8"))          

 
        #for uut in vtep_uut_list:
        if not TriggerCoreIfFlap222(esi_uut_list): 
            log.info("TriggerCoreIfFlap222 failed @ 4")
            self.failed()
    
        countdown(100)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC85_Routed_Triggers_VPC_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC86_Routed_Triggers_ESI_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass



class TC87_Routed_Triggers_VPC_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     

 

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC88_Routed_Triggers_ESI_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     

 

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


 

 

class TC89_Routed_Triggers_VPC_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

 

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC90_Routed_Triggers_ESI_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

 

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass




class TC91_Routed_Triggers_VPC_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC92_Routed_Triggers_ESI_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass





class TC93_Routed_Triggers_VPC_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in vpc_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC94_Routed_Triggers_ESI_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in esi_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass


class TC95_Routed_Triggers_Spine_ClearIpRoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


    @aetest.test
    def Trigger6ClearIpRoute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))         

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip route *")
 
        countdown(60)

        #log.info(banner("-------triggering peer Learning------"))
        
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

  
    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass

        
class TC96_Routed_Triggers_Spine_ClearIpMoute(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         


   
 
    @aetest.test
    def Trigger7ClearIpMroute(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpRoute @ 11"))     

 

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip mroute *")

    
        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
         
class TC97_Routed_Triggers_Spine_Clear_OSPF(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
         
 
   
    @aetest.test
    def Trigger8ClearOspfNeigh(self, testscript, testbed):
        log.info(banner("Starting TriggerClearOspfNeigh @ 11"))     

 

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip ospf neighbor *")
    
        countdown(60)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
    
class TC98_Routed_Triggers_Spine_Clear_IP_Bgp(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    


    @aetest.test
    def Trigger9ClearIpBgp(self, testscript, testbed):
        log.info(banner("Starting TriggerClearIpBgp @ 11"))     


        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear ip bgp *")
     
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
class TC99_Routed_Triggers_Spine_Clear_Bgp_l2vpn(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    

 
    @aetest.test
    def Trigger10ClearBgpL2vpnEvpn(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in spine_uut_list:
            for i in range(1,3):
                uut.execute("clear bgp l2vpn evpn *")
                #uut.execute(' clear bgp all *')
        countdown(80)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        

class TC100_Routed_Triggers_VPC_Clear_ARP_MAC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



 
    @aetest.test
    def Trigger11ClearArpMac(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in vpc_uut_list:
            for i in range(1,5):
                uut.execute("clear ip arp vrf all")
                uut.execute("clear mac add dy")                              

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        


class TC101_Routed_Triggers_ESI_Clear_ARP_MAC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



 
    @aetest.test
    def Trigger11ClearArpMac(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in esi_uut_list:
            for i in range(1,5):
                uut.execute("clear ip arp vrf all")
                uut.execute("clear mac add dy")                              

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])


    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        




class TC102_Routed_Triggers_VPC_nve_Bounce(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



  
    @aetest.test
    def Trigger12NveShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 
                    

        for uut in vpc_uut_list:
            cmd1 = \
                """
                interface nve 1
                shut
                """
            uut.configure(cmd1)
        countdown(5)                  
        for uut in vpc_uut_list:
            cmd2 = \
                """
                interface nve 1
                no shut
                """
            uut.configure(cmd2)

        countdown(60)


        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
        

class TC103_Routed_Triggers_ESI_nve_Bounce(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    



  
    @aetest.test
    def Trigger12NveShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 
                    

        for uut in esi_uut_list:
            cmd1 = \
                """
                interface nve 1
                shut
                """
            uut.configure(cmd1)
        countdown(5)                  
        for uut in esi_uut_list:
            cmd2 = \
                """
                interface nve 1
                no shut
                """
            uut.configure(cmd2)

        countdown(60)


        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
      

class TC104_Routed_Triggers_VLAN_Bounce_VPC(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    




 
    @aetest.test
    def Trigger15VlanShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in vpc_uut_list:
            vlanshut = \
            """
            vlan {vlan_range}
            shut
            end
            """
            uut.configure(vlanshut.format(vlan_range=vlan_range))  
        countdown(5)
        for uut in vpc_uut_list:
            vlannoshut = \
            """
            vlan {vlan_range}
            no shut
            end
            """
            uut.configure(vlannoshut.format(vlan_range=vlan_range))                        

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        


        

class TC105_Routed_Triggers_VLAN_Bounce_ESI(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
 
    @aetest.test
    def Trigger15VlanShutNoshut(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

 

        for uut in esi_uut_list:
            vlanshut = \
            """
            vlan {vlan_range}
            shut
            end
            """
            uut.configure(vlanshut.format(vlan_range=vlan_range))  
        countdown(5)
        for uut in esi_uut_list:
            vlannoshut = \
            """
            vlan {vlan_range}
            no shut
            end
            """
            uut.configure(vlannoshut.format(vlan_range=vlan_range))                        

        countdown(60)

        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """
        pass
        
                

class TC106_Routed_Triggers_VPC_Z_Flow1(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
 
 
    @aetest.test
    def Trigger13Zflow1(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep1.interfaces.keys():
            if 'vpc_po' in vtep1.interfaces[intf].type:
                vpc5 = vtep1.interfaces[intf].intf
                vtep1.configure(poshut.format(po=vpc5)) 

        for intf in vtep2.interfaces.keys():
            if 'l3_po' in vtep2.interfaces[intf].type:
                l3po6 = vtep2.interfaces[intf].intf
                vtep2.configure(poshut.format(po=l3po6)) 


 
        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep1.configure(ponoshut.format(po=vpc5)) 
            vtep2.configure(ponoshut.format(po=l3po6))
            countdown(60)
            self.failed() 

        vtep1.configure(ponoshut.format(po=vpc5)) 
        vtep2.configure(ponoshut.format(po=l3po6))

        countdown(100)
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
 

    @aetest.cleanup
    def cleanup(self):
        """ testcase clean up """

        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep1.interfaces.keys():
            if 'vpc_po' in vtep1.interfaces[intf].type:
                vpc5 = vtep1.interfaces[intf].intf
                vtep1.configure(ponoshut.format(po=vpc5)) 

        for intf in vtep2.interfaces.keys():
            if 'l3_po' in vtep2.interfaces[intf].type:
                l3po6 = vtep2.interfaces[intf].intf
                vtep2.configure(ponoshut.format(po=l3po6)) 

 
class TC107_Routed_Triggers_VPC_Z_Flow2(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
     

    @aetest.test
    def Trigger14Zflow2(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep2.interfaces.keys():
            if 'vpc_po' in vtep2.interfaces[intf].type:
                vpc6 = vtep2.interfaces[intf].intf
                vtep2.configure(poshut.format(po=vpc6)) 

        for intf in vtep1.interfaces.keys():
            if 'l3_po' in vtep1.interfaces[intf].type:
                l3po5 = vtep1.interfaces[intf].intf
                vtep1.configure(poshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep2.configure(ponoshut.format(po=vpc6))  
            vtep1.configure(ponoshut.format(po=l3po5))
            countdown(60)
            self.failed()

        vtep2.configure(ponoshut.format(po=vpc6))  
        vtep1.configure(ponoshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
        
        countdown(120) 
    
    @aetest.cleanup
    def cleanup(self):


        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep2.interfaces.keys():
            if 'vpc_po' in vtep2.interfaces[intf].type:
                vpc6 = vtep2.interfaces[intf].intf
                vtep2.configure(ponoshut.format(po=vpc6)) 

        for intf in vtep1.interfaces.keys():
            if 'l3_po' in vtep1.interfaces[intf].type:
                l3po5 = vtep1.interfaces[intf].intf
                vtep1.configure(ponoshut.format(po=l3po5))
       
       
        for port_hdl in port_handle_list:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'stop', db_file=0 ) 
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'reset') 

 
class TC108_Routed_Triggers_ESI_Failover(aetest.Testcase):
    ###    This is description for my tecase two
  
    @aetest.setup
    def setup(self):
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed(goto=['cleanup'])
    
     

    @aetest.test
    def TriggerESIFailover(self, testscript, testbed):
        log.info(banner("Starting TriggerClearBgpL2vpnEvpn @ 11"))     

        poshut = \
            """
            interface po{po}
            shut
            """
        ponoshut = \
            """
            interface po{po}
            no shut
            """

        for intf in vtep3.interfaces.keys():
            if 'esi_po' in vtep3.interfaces[intf].type:
                esi = vtep3.interfaces[intf].intf
                vtep3.configure(poshut.format(po=esi)) 

 
        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        if not test1:
            log.info(banner("Rate test Failed"))
            vtep3.configure(ponoshut.format(po=esi))  
            #vtep1.configure(ponoshut.format(po=l3po5))
            countdown(60)
            self.failed()

        vtep3.configure(ponoshut.format(po=esi))  
        #vtep1.configure(ponoshut.format(po=l3po5))

        countdown(130)
     
        test1=SpirentRateTest22(port_handle_sw1,port_handle_sw2,rate,int(pps))
        
        if not test1:
            log.info(banner("Rate test Failed"))
            self.failed()

        for port_hdl in [port_handle_vtep1,port_handle_vtep2,port_handle_vtep3,port_handle_vtep4,port_handle_vtep5]:
            res = sth.drv_stats(query_from = port_hdl,properties = "Port.TxTotalFrameRate Port.RxTotalFrameRate")
            rx_rate = res['item0']['PortRxTotalFrameRate']
            log.info('+--------------------------------------+')  
            log.info('+---- RX rate at Port %r is : %r ------+',port_hdl,rx_rate) 
            log.info('+--------------------------------------+') 
            if abs(int(rx_rate) - int(rate)*2) < int(pps):
                log.info('Traffic  Rate Test failed for %r',port_hdl)
                log.info('Stats are %r',res)
                self.failed(goto=['TC35_Unicast_Triggers'])
        
        countdown(120) 
    
    @aetest.cleanup
    def cleanup(self):

        ponoshut = \
            """
            interface po{po}
            no shut
            """


        for intf in vtep3.interfaces.keys():
            if 'esi_po' in vtep2.interfaces[intf].type:
                esi = vtep2.interfaces[intf].intf
                vtep3.configure(poshut.format(po=esi)) 

       
        for port_hdl in  port_handle_list:
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'stop', db_file=0 ) 
            traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'reset') 

  
 
class common_cleanup(aetest.CommonCleanup):

    @aetest.subsection
    def stop_tgn_streams(self):
        pass
    
    @aetest.subsection
    def stop_tgn_streams(self):
        pass
        #for port_hdl in  port_handle_list:
        #    traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'stop', db_file=0 ) 
        #    traffic_ctrl_ret = sth.traffic_control(port_handle = port_hdl, action = 'reset') 
 


    #@aetest.subsection
    #def disconnect_from_tgn(self):
        #general_lib.cleanup_tgn_config(cln_lab_srvr_sess = 1)
        #pass

if __name__ == '__main__':  # pragma: no cover
    aetest.main()
 

 
 