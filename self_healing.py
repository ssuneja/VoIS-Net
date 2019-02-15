import _csv, os, threading, re
from napalm import get_network_driver
from netmiko.ssh_dispatcher import ConnectHandler


CONTROLLER_IP= "172.16.3.15"
USERNAME= 'batman'
PASSWORD= '7654321'
MY_OVSES= ['1', '2', '3']
NETWORK_TRUTH= 'network_truth.csv'
BRIDGE= 'br0'
connected_ovses= []
disconnected_ovses= []
version_match_ovses= []
version_mismatch_ovses= []



'''
Returns dpid, controller ip and of_version configured on a switch 
given the mgmt IP of a switch
'''
def parse_this_switch(switch_mgmt_ip):
    if os.path.isfile(NETWORK_TRUTH):
        with open('inventory.csv') as csvfile:
            reader=_csv.reader(csvfile)
            
            for row in reader:
                if row[1]== switch_mgmt_ip:
                    '''
                    The function call should have: switch_dpid, controller_ip, of_versions 
                    to catch rows 0,1,2 respectively
                    '''
                    return(row[0], row[1], row[2])
            
            csvfile.close()

    else:
        ######Replace print with log later
        print("Please add network truth csv file immediately")
        return(None, None, None)


'''
Returns list of mgmt IPs of all switches
as reflected in csv file
'''
def get_my_switches(self):
    my_switch_mgmt_ips= []

    if os.path.isfile(NETWORK_TRUTH):
        with open('inventory.csv') as csvfile:
            reader=_csv.reader(csvfile)

            for row in reader:
                if row[0]!= "Switch DPID":
                    my_switch_mgmt_ips.append(row[1])
            
            return(my_switch_mgmt_ips)
            csvfile.close()

    else:
        ######Replace print with log later
        print("Please add network truth csv file immediately")
        return(None)



class Check_Ctl_Connectivity(threading.Thread):
    def __init__(self, net_device):
        threading.Thread.__init__(self)
        self.net_device= net_device
    
    def run(self):
        self.net_connect= ConnectHandler(**self.net_device)
        self.net_connect.find_prompt()
        output= self.net_connect.send_command_timing("sudo -S <<< 7654321 ovs-vsctl show | grep is_connected", strip_command= False, strip_prompt= False)
        output= output.split('\n')[1]
        
        if 'true' in output:
            connected_ovses.append(self.net_device['ip'])
        
        else:
            #disconnected_ovses.append(self.net_device['ip'])
            command= "sudo -S <<< 7654321 ovs-vsctl get-controller {}".format(BRIDGE)
            controller_config= self.net_connect.send_command_timing(command, strip_command= False, strip_prompt= False)
            controller_config= controller_config.split('\n')[1]

            
            of_ver= self.net_connect.send_command_timing("sudo -S <<< 7654321 ovs-vsctl get bridge br0 protocols", 
                                                               strip_command= False, strip_prompt= False)
            of_ver= of_ver.split('\n')[1]
            of_versions= re.findall(r'OpenFlow\d+', of_ver)
            
            disconnected_ovses.append({'switch_mgmt_ip': self.net_device['ip'],
                                       'controller_config': controller_config,
                                       'of_versions': of_versions, 
                                        })
        

class Check_Ver_Mismatch(threading.Thread):
    def __init__(self, ip, of_versions):
        threading.Thread.__init__(self)
        self.ip= ip
        self.of_versions= of_versions
    
    def run(self):
        self.net_connect= ConnectHandler(**self.net_device)
        self.net_connect.find_prompt()
        switch_dpid, true_controller_ip, true_of_version= parse_this_switch(self.ip)
        
        if true_of_version in self.of_versions:
            version_match_ovses.append(self.ip)
        
        else:
            version_mismatch_ovses.append(self.ip)


class Detect_Issues():
    def __init__(self):
        pass
    
    #Calls threads to check ctl connectivity for all switches
    def check_controller_conn(self):
        global connected_ovses, disconnected_ovses
        #my_switches_mgmt_ips= ['172.16.3.10', '172.16.3.11', '172.16.3.13', '172.16.3.14'] #get_my_switches()
        my_switches_mgmt_ips= get_my_switches()
        #Check Connectivity to controller
        threads= []
        for ip in my_switches_mgmt_ips:
            self.net_device={
                'device_type':'linux',
                'ip': ip,
                'username': USERNAME,
                'use_keys': 'True',
                }
            
            thr_check_ctl_conn= Check_Ctl_Connectivity(self.net_device)
            thr_check_ctl_conn.daemon= True
            thr_check_ctl_conn.start()
            threads.append(thr_check_ctl_conn)
        
        for element in threads:
            element.join()
        
        #print("Connected OVSes")
        #print(connected_ovses)
        #print("Disconnected OVSes")
        #print(disconnected_ovses)
        connected_ovses1= connected_ovses
        disconnected_ovses1= disconnected_ovses
        connected_ovses= []
        disconnected_ovses= []
        return(connected_ovses1, disconnected_ovses1)


    #Calls threads to check version mismatch of disconnected switches provided as argument
    def check_ver_mismatch(self, disconnected_ovses):
        self.disconnected_ovses= disconnected_ovses
        threads= []
        for ovs in self.disconnected_ovses: 
            thr_check_ver_mismatch= Check_Ver_Mismatch(ovs['switch_mgmt_ip'], ovs['of_versions'])
            thr_check_ver_mismatch.daemon= True
            thr_check_ver_mismatch.start()
            threads.append(thr_check_ver_mismatch)
        
        for element in threads:
            element.join()
        
        print("Matched versions")
        print(version_match_ovses)
        print("Mismatched versions")
        print(version_mismatch_ovses)
        
        
        
#Get Disconnected switches list    
obj= Detect_Issues()
connected_ovses, disconnected_ovses= obj.check_controller_conn()
print("Connected OVSes:")
print(connected_ovses)
print("Disconencted OVSes")
print(disconnected_ovses)


#Get ver mismatched switches list

disconnected_ovses['ip'], disconnected_ovses['of_versions']

    
    
    
