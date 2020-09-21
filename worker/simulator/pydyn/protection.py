from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF, BASE_KV
from pypower.idx_brch import *
import numpy as np
from decimal import *
from collections import defaultdict
import warnings

getcontext().prec = 6

# TODO One to many connection implementation

class InstantaneousElement(object):
    def __init__(self, label, ppc, sampling_interval):
        '''
            label: label assigned to the element
            ppc: power network data
            sampling_interval: sampling interval of the element
        '''
        self.label = label
        self.sampling_interval = sampling_interval  # This is integer
        self.ports = {"CMD_OPEN": False, "TRIP_SEND": False,
                      'MISSED': False, 'SPURIOUS': False,
                      'TRIP_RECIEVE': False}
        self.current_state = "IDLE"
        self.to_be_updated = []
        self.port_mappings = {}

    def add_connection(self, internal_port, external_element, dst_internal_port):
        '''
            Port mapping occurs between ports of same label
            intrenal_port is the source port
            and the port with the same name in external_element
            is the destination port 
        '''
        if dst_internal_port is None:
            dst_internal_port = internal_port
        assert internal_port in self.ports.keys(), "Source port label not found"
        assert dst_internal_port in external_element.ports.keys(
        ), "Destination port label not found"
        self.port_mappings.update({internal_port: (external_element, dst_internal_port)})

    def check_condition(self, vprev):
        assert True, 'Cannot call base class'

    def step(self, vprev, events):
        if self.current_state == "IDLE":
            if self.ports["MISSED"]:
                self.current_state = "MISSED"
                return None
            if self.check_condition(vprev) or self.ports['SPURIOUS']:
                self.current_state = "TRIPPED"
                self.ports["CMD_OPEN"] = True
                self.ports['TRIP_SEND'] = True
                self.to_be_updated.extend(['CMD_OPEN', 'TRIP_SEND'])
                return None
            return self.sampling_interval
        else:
            return None

    def update_port_interfaces(self):
        for internal_port in self.to_be_updated:
            dst_element, dst_internal_port = self.port_mappings[internal_port]
            dst_element.ports[dst_internal_port] = self.ports[internal_port]
        self.to_be_updated = []

class TimeDelayedElement(InstantaneousElement):
    def __init__(self, label, ppc, sampling_interval, delay):
        super().__init__(label, ppc, sampling_interval)
        self.delay = delay
        assert sampling_interval < delay, "delay cannot be smaller than sampling interval"
        self.delay_ticks = int(delay/sampling_interval)
        self.tick_counter = 0

    def step(self, vprev, elements):
        if self.current_state == "IDLE":
            if self.ports["MISSED"]:
                self.current_state = "MISSED"
                return None
            if self.check_condition(vprev) or self.ports['SPURIOUS']:
                self.current_state = "WAIT"
                return None
            if self.ports['SPURIOUS']:
                self.current_state = "WAIT_FAULT"
                return None
            return self.sampling_interval
        elif self.current_state == "WAIT":
            if (self.ports['TRIP_RECIEVE']) or \
                    (self.check_condition(vprev) and self.tick_counter >= self.delay_ticks):
                self.current_state = "TRIPPED"
                self.ports['CMD_OPEN'] = True
                self.ports['TRIP_RECIEVED'] = False
                self.to_be_updated.append('CMD_OPEN')
                self.tick_counter = 0
                return None
            elif not self.check_condition(vprev):
                self.current_state = "IDLE"
                self.tick_counter = 0
                return self.sampling_interval
            self.tick_counter += 1
            return self.sampling_interval
        elif self.current_state == "FAULT_WAIT":
            if self.ports['TRIP_RECIEVE'] or self.tick_counter >= self.delay_ticks:
                self.current_state = "TRIPPED"
                self.ports['CMD_OPEN'] = True
                self.ports['TRIP_RECIEVED'] = False
                self.to_be_updated.append('CMD_OPEN')
                self.tick_counter = 0
                return None
            self.tick_counter += 1
            return self.sampling_interval
        else:
            return None

class InstantaneousBusElement(InstantaneousElement):
    def __init__(self, label, ppc, sampling_interval, bus_id):
        # TODO parameter type checking
        super().__init__(label, ppc, sampling_interval)
        self.bus_idx = bus_id 
        self.bus_id = bus_id - 1 # internal

class InstantaneousBranchElement(InstantaneousElement):
    def __init__(self, label, ppc, sampling_interval, to_bus, from_bus, branch_id):
        # TODO parameter type checking
        super().__init__(label, ppc, sampling_interval)
        self.to_bus_idx = to_bus 
        self.to_bus = to_bus - 1 # internal
        self.from_bus_idx = from_bus 
        self.from_bus = from_bus - 1 # interbal
        self.to_bus_BaseKV = ppc['bus'][self.to_bus, BASE_KV]
        self.from_bus_BaseKV = ppc['bus'][self.from_bus, BASE_KV]
        r = ppc['branch'][branch_id, BR_R]
        x = ppc['branch'][branch_id, BR_X]
        ys = 1/np.complex(r, x)
        b = ppc['branch'][branch_id, BR_B]
        jbc_by_2 = np.complex(0, b/2)
        theta_shift = ppc['branch'][branch_id, SHIFT]
        tau = ppc['branch'][branch_id, TAP]
        if tau == 0:
            tau = 1
        self.Y_br = np.zeros((2, 2), dtype=complex)
        self.Y_br[0][0] = (ys + jbc_by_2) * (1/tau**2)
        self.Y_br[0][1] = (-ys / (tau * np.exp(np.complex(0, -theta_shift))))
        self.Y_br[1][0] = (-ys / (tau * np.exp(np.complex(0, theta_shift))))
        self.Y_br[1][1] = (ys + jbc_by_2)

class TimeDelayedBusElement(TimeDelayedElement):
    def __init__(self, label, ppc, sampling_interval, delay, bus_id):
        super().__init__(label, ppc, sampling_interval, delay)
        self.bus_idx = bus_id 
        self.bus_id =  bus_id - 1 # internal

class TimeDelayedBranchElement(TimeDelayedElement):
    def __init__(self, label, ppc, sampling_interval, delay, to_bus, from_bus, branch_id):
        super().__init__(label, ppc, sampling_interval, delay)
        '''
        MATPOWER Branch Model
        Y_br =  [ [(ys + jbc/2) * 1/tau^2, -ys * (1/(tau * e^(-j*theta)))],
                  [-ys * (1/(tau * e^(j*theta))), ys + jbc/2] ]
        '''
        self.to_bus_idx = to_bus 
        self.to_bus = to_bus - 1 # internal
        self.from_bus_idx = from_bus 
        self.from_bus =  from_bus - 1 # internal
        self.to_bus_BaseKV = ppc['bus'][self.to_bus, BASE_KV]
        self.from_bus_BaseKV = ppc['bus'][self.from_bus, BASE_KV]
        r = ppc['branch'][branch_id, BR_R]
        x = ppc['branch'][branch_id, BR_X]
        ys = 1/np.complex(r,x)
        b = ppc['branch'][branch_id, BR_B]
        jbc_by_2 = np.complex(0,b/2)
        theta_shift = ppc['branch'][branch_id, SHIFT]
        tau = ppc['branch'][branch_id, TAP]
        if tau == 0:
            tau = 1
        self.Y_br = np.zeros((2,2), dtype=complex)
        self.Y_br[0][0] = (ys + jbc_by_2) * (1/tau**2)
        self.Y_br[0][1] = (-ys / (tau * np.exp(np.complex(0,-theta_shift))))
        self.Y_br[1][0] = (-ys / (tau * np.exp(np.complex(0, theta_shift))))
        self.Y_br[1][1] = (ys + jbc_by_2)

class InstantaneousOvercurrentElement(InstantaneousBranchElement):
    def __init__(self, label, ppc, sampling_interval, to_bus, from_bus, branch_id, i_thresh):
        super().__init__(label, ppc, sampling_interval, to_bus, from_bus, branch_id)
        self.i_thresh = i_thresh

    def check_condition(self, vprev):
        V = np.zeros((2, 1))
        V[0][0] = self.to_bus_BaseKV * np.abs(vprev[self.to_bus_idx])
        V[1][0] = self.from_bus_BaseKV * np.abs(vprev[self.from_bus_idx])
        I = self.Y_br * V
        return I[0][0] > self.i_thresh

class TimeDelayedOvercurrentElement(TimeDelayedBranchElement):
    def __init__(self, label, ppc, sampling_interval, delay, to_bus, from_bus, branch_id, i_thresh):
        super().__init__(label, ppc, sampling_interval, delay, to_bus, from_bus, branch_id)
        self.i_thresh = i_thresh
    
    def check_condition(self, vprev):
        V = np.zeros((2, 1))
        V[0][0] = self.to_bus_BaseKV * np.abs(vprev[self.to_bus_idx])
        V[1][0] = self.from_bus_BaseKV * np.abs(vprev[self.from_bus_idx])
        I = self.Y_br * V
        return I[0][0] > self.i_thresh

class InstantaneousZoneElement(InstantaneousBranchElement):
    def __init__(self, label, ppc, sampling_interval, to_bus, from_bus, branch_id, z_thresh):
        super().__init__(label, ppc, sampling_interval, to_bus, from_bus, branch_id)
        self.z_thresh = z_thresh
        self.v_prev = None
        self.i_prev = None
        self.flag = False
    
    def check_condition(self, vprev):
        V = np.zeros((2, 1))
        V[0][0] = self.to_bus_BaseKV * np.abs(vprev[self.to_bus_idx])
        V[1][0] = self.from_bus_BaseKV * np.abs(vprev[self.from_bus_idx])
        I = self.Y_br * V
        # TODO Implement distance relay logic
        return False
        
class TimeDelayedZoneElement(TimeDelayedBranchElement):
    def __init__(self, label, ppc, sampling_interval, delay, to_bus, from_bus, branch_id, z_thresh):
        super().__init__(label, ppc, sampling_interval, delay, to_bus, from_bus, branch_id)
        self.z_thresh = z_thresh
        self.v_prev = None
        self.i_prev = None
        self.flag = False
    
    def check_condition(self, vprev):
        V = np.zeros((2, 1))
        V[0][0] = self.to_bus_BaseKV * np.abs(vprev[self.to_bus_idx])
        V[1][0] = self.from_bus_BaseKV * np.abs(vprev[self.from_bus_idx])
        I = self.Y_br * V
        # TODO Implement distance relay logic
        return False

class Relay(object):
    def __init__(self, sampling_interval, label):
        self.label = label
        self.elements = []
        self.sampling_interval = sampling_interval

    def add_connection(self, src_element_label, internal_port, external_object, dst_element_label=None, dst_internal_port=None):
        for src_element in self.elements:
            if src_element.label == src_element_label:
                if isinstance(external_object, Relay):
                    for dst_element in external_object:
                        if dst_element.label == dst_element_label:
                            src_element_label.add_connection(
                                internal_port, dst_element, dst_internal_port)
                elif isinstance(external_object, Breaker):
                    src_element.add_connection(internal_port, external_object, dst_internal_port)
    
    def step(self, vprev, events):
        next_invocation = []
        for element in self.elements:
            next_invocation.append(element.step(vprev, elements))
        if self.sampling_interval in next_invocation:
            return self.sampling_interval
        else:
            return None
    
    def update_interfaces(self):
        for element in self.elements:
            element.update_interfaces()

class OverCurrentProtection(Relay):
    def __init__(self, i1_thresh, i2_thresh, i3_thresh, i2_delay, i3_delay, 
                label, ppc, sampling_interval, to_bus, from_bus, branch_id):
        super().__init__(sampling_interval, label)
        self.elements.append(InstantaneousOvercurrentElement(label+'O1', ppc, 
                                sampling_interval, to_bus, from_bus, branch_id, i1_thresh))
        self.elements.append(TimeDelayedOvercurrentElement(label+'O2', ppc, 
                            sampling_interval, i2_delay, to_bus, from_bus, branch_id, i2_thresh))
        self.elements.append(TimeDelayedOvercurrentElement(label+'O3', ppc,
                            sampling_interval, i3_delay, to_bus, from_bus, branch_id, i3_thresh))

class DistanceProtection(Relay):
    def __init__(self, z1_thresh, z2_thresh, z3_thresh, z2_delay, z3_delay,
                label, ppc, sampling_interval, to_bus, from_bus, branch_id):
        super().__init__(sampling_interval, label)
        self.elements.append(InstantaneousZoneElement(label+'_Z1', ppc, 
                                sampling_interval,to_bus, from_bus, branch_id, z1_thresh))
        self.elements.append(TimeDelayedZoneElement(label+'_Z2', ppc, sampling_interval, 
                                        z2_delay, to_bus, from_bus, branch_id, z2_thresh))
        self.elements.append(TimeDelayedZoneElement(label+'_Z3', ppc, sampling_interval, 
                                        z3_delay, to_bus, from_bus, branch_id, z3_thresh))
    
class OverloadProtection(Relay):
    def __init__(self, i1_thresh, i2_thresh, i3_thresh, i1_delay, i2_delay, i3_delay,
                 label, ppc, sampling_interval, to_bus, from_bus, branch_id):
        super().__init__(sampling_interval, label)
        self.elements.append(TimeDelayedOvercurrentElement(label+'O1', ppc,
                                                           sampling_interval, i1_delay, to_bus, from_bus, branch_id, i1_thresh))
        self.elements.append(TimeDelayedOvercurrentElement(label+'O2', ppc,
                                                           sampling_interval, i2_delay, to_bus, from_bus, branch_id, i2_thresh))
        self.elements.append(TimeDelayedOvercurrentElement(label+'O3', ppc,
                                                           sampling_interval, i3_delay, to_bus, from_bus, branch_id, i3_thresh))

class Breaker(object):
    def __init__(self, label, sampling_interval, tto, ttc, branch_id):
        self.label = label
        self.branch_id = branch_id
        self.ticks_tto = int(tto/sampling_interval)
        self.ticks_ttc = int(ttc/sampling_interval)
        self.tick_counter = 0
        self.current_state = "CLOSED"
        self.ports = {"CMD_OPEN": False, "CMD_CLOSE": False}
        self.sampling_interval = sampling_interval

    def step(self, vprev, events):
        if (self.current_state == "CLOSED"):
            if (self.ports["CMD_OPEN"]):
                self.ports["CMD_OPEN"] = False
                self.current_state = "OPENING"
                self.tick_counter = 0

        elif (self.current_state == "OPENING"):
            if (self.tick_counter >= self.ticks_tto):
                self.current_state = "OPEN"
                self.tick_counter = 0
                events.event_stack.append(
                    [self.time, "TRIP_BRANCH", self.branch_id])
            else:
                self.tick_counter += 1

        elif (self.current_state == "OPEN"):
            if (self.ports["CMD_CLOSE"]):
                self.current_state = "CLOSING"
                self.ports["CMD_CLOSE"] = False
                self.tick_counter = 0
        else:
            if (self.tick_counter >= self.ticks_ttc):
                self.current_state = "CLOSED"
                self.tick_counter = 0
                # TODO Implement CONNECT_BUS
            else:
                self.tick_counter += 1

        return self.sampling_interval

    def update_interfaces(self):
        pass

    def add_connection(self):
        pass

class EventInjector(object):
    def __init__(self):
        self.ports = {}
        self.port_mappings = defaultdict(list)
        self.ticks_to_fire = []
        self.ports_to_be_updated = [[]]
        
    def get_device_label(self, event):
        label = 'PA_'
        if event['equipment'] == 'relay':
            if event['kind'] == 'distance':
                label += 'DR_'
            elif event['kind'] == 'over-current':
                label += 'OR_'
            else:
                pass
        elif event['equipment'] == 'breaker':
            label += 'BR_'
        label += '{}_{}'.format(event['from_bus'], event['to_bus'])
        return label


    def add_events(self, list_of_events, protection_devices, simulation_step, pseudo_bus_map):
        device_dict = {device.label :  device for device in protection_devices}
        list_of_events = sorted(list_of_events, key=lambda k: k['time'])
        previous_time = 0
        self.ports_to_be_updated = [[]]
        for event in list_of_events:
            # ticks = event['time'][1]/simulation_step
            # self.ticks_to_fire.append(ticks)
            
            # port label for event injector is device label + type
            device_label = self.get_device_label(event)
            port = event["type"].upper()
            port = port.replace(' ', '_')
            port_label = device_label + "_{}".format(port)
            self.ports.update({ port_label: False})
            self.add_connection(port_label, device_dict[device_label], port)
            delta_time = event['time'][1] - previous_time
            previous_time = event['time'][1] 
            if delta_time > 0 :
                ticks = int(delta_time/simulation_step)
                self.ticks_to_fire.append(ticks)
                self.ports_to_be_updated.append([port_label])
            elif delta_time == 0:
                self.ports_to_be_updated[-1].append(port_label)
            else:
                warnings.warn("delta cannot be negative")
            
    def add_connection(self, internal_port, external_device, dst_internal_port):
        # This is a one to many connection 
        if isinstance(external_device, InstantaneousElement) or \
            isinstance(external_device, Breaker):
            if dst_internal_port in external_device.ports.keys():
                self.port_mappings[internal_port].append([external_device, dst_internal_port])

        elif isinstance(external_device, Relay):
            for element in external_device.elements:
                if dst_internal_port in element.ports.keys():
                    self.port_mappings[internal_port].append([external_device, dst_internal_port])

        else:
            warnings.warn("Cannot identify the type of the external_device")

    def step(self, a, b):
        ports = self.ports_to_be_updated.pop(0)
        for port in ports:
            for element_port_pair in self.port_mappings[port]:
                element_port_pair[0].ports[element_port_pair[1]] = True 
        if len(self.ticks_to_fire) > 0:
            return self.ticks_to_fire.pop(0)
        else:
            return None

    def update_interfaces(self):
        pass


