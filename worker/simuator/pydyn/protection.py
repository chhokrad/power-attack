from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF, BASE_KV
from pypower.idx_brch import *
import numpy as np
from decimal import *

getcontext().prec = 6


class InstantaneousElement(object):
    def __init__(self, label, ppc, sampling_interval):
        '''
            label: label assigned to the element
            ppc: power network data
            sampling_interval: sampling interval of the element
        '''
        self.label = label
        self.sampling_interval = sampling_interval  # This is integer
        self.ports = {"CMD_OPEN": False, "TRIP": False,
                      'MISSED': False, 'SPURIOUS': False}
        self.current_state = "IDLE"
        self.to_be_updated = []
        self.port_mappings = {}

    def add_connection(self, internal_port, external_element):
        '''
            Port mapping occurs between ports of same label
            intrenal_port is the source port
            and the port with the same name in external_element
            is the destination port
        '''
        assert internal_port in self.ports.keys(), "Source port label not found"
        assert internal_port in external_element.ports.keys(
        ), "Destination port label not found"
        self.port_mappings.update({internal_port: external_element})

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
                self.ports['TRIP'] = True
                self.to_be_updated.extend(['CMD_OPEN', 'TRIP'])
                return None
            return self.sampling_interval
        else:
            return None

    def update_port_interfaces(self):
        for internal_port, external_element in self.port_mappings:
            # TODO Implement checks
            if internal_port in self.to_be_updated:
                external_element.ports[internal_port] = self.ports[internal_port]
        self.to_be_updated = []

class TimeDelayedElement(InstantaneousElement):
    def __init__(self, label, ppc, sampling_interval, delay):
        super().__init__(label, ppc, sampling_interval)
        self.delay = delay
        assert sampling_interval >= delay, "delay cannot be smaller than sampling interval"
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
            if (self.ports['TRIP']) or \
                    (self.check_condition(vprev) and self.tick_counter >= self.delay_ticks):
                self.current_state = "TRIPPED"
                self.ports['CMD_OPEN'] = True
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
            if self.ports['TRIP'] or self.tick_counter >= self.delay_ticks:
                self.current_state = "TRIPPED"
                self.ports['CMD_OPEN'] = True
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

class InstantaneousBranchElement(InstantaneousElement):
    def __init__(self, label, ppc, sampling_interval, to_bus, from_bus, branch_id):
        # TODO parameter type checking
        super().__init__(label, ppc, sampling_interval)
        self.to_bus_idx = to_bus
        self.from_bus_idx = from_bus
        self.to_bus_BaseKV = ppc['bus'][to_bus, BASE_KV]
        self.from_bus_BaseKV = ppc['bus'][from_bus, BASE_KV]
        r = ppc['branch'][branch_id, BR_R]
        x = ppc['branch'][branch_id, BR_X]
        ys = 1/np.complex(r, x)
        b = ppc['branch'][branch_id, BR_B]
        jbc_by_2 = np.complex(0, b/2)
        theta_shift = ppc['branch'][branch_id, SHIFT]
        tau = ppc['branch'][branch_id, TAP]
        self.Y_br = np.zeros((2, 2))
        self.Y_br[0][0] = (ys + jbc_by_2) * (1/tau**2)
        self.Y_br[0][1] = (-ys / (tau * np.exp(np.complex(0, -theta_shift))))
        self.Y_br[1][0] = (-ys / (tau * np.exp(np.complex(0, theta_shift))))
        self.Y_br[1][1] = (ys + jbc_by_2)

class TimeDelayedBusElement(TimeDelayedElement):
    def __init__(self, label, ppc, sampling_interval, delay, bus_id):
        super().__init__(label, ppc, sampling_interval, delay)
        self.bus_idx = bus_id

class TimeDelayedBranchElement(TimeDelayedElement):
    def __init__(self, label, ppc, sampling_interval, delay, to_bus, from_bus, branch_id):
        super().__init__(label, ppc, sampling_interval, delay)
        '''
        MATPOWER Branch Model
        Y_br =  [ [(ys + jbc/2) * 1/tau^2, -ys * (1/(tau * e^(-j*theta)))],
                  [-ys * (1/(tau * e^(j*theta))), ys + jbc/2] ]
        '''
        self.to_bus_idx = to_bus
        self.from_bus_idx = from_bus
        self.to_bus_BaseKV = ppc['bus'][to_bus, BASE_KV]
        self.from_bus_BaseKV = ppc['bus'][from_bus, BASE_KV]
        r = ppc['branch'][branch_id, BR_R]
        x = ppc['branch'][branch_id, BR_X]
        ys = 1/np.complex(r,x)
        b = ppc['branch'][branch_id, BR_B]
        jbc_by_2 = np.complex(0,b/2)
        theta_shift = ppc['branch'][branch_id, SHIFT]
        tau = ppc['branch'][branch_id, TAP]
        self.Y_br = np.zeros((2,2))
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

class OverCurrentProtection(object):
    pass

class DistanceProtection(object):
    def __init__(self, z1_thresh, z2_thresh, z3_thresh, z2_delay, z3_delay,
                label, ppc, sampling_interval, to_bus, from_bus, branch_id):
        self.elements = []
        self.sampling_interval = sampling_interval
        self.elements.append(InstantaneousZoneElement(label+'_Z1', ppc, 
                                sampling_interval,to_bus, from_bus, branch_id, z1_thresh))
        self.elements.append(TimeDelayedZoneElement(label+'_Z2', ppc, sampling_interval, 
                                        z2_delay, to_bus, from_bus, branch_id, z2_thresh))
        self.elements.append(TimeDelayedZoneElement(label+'_Z3', ppc, sampling_interval, 
                                        z3_delay, to_bus, from_bus, branch_id, z3_thresh))
    
    def add_connection(self, src_element_label, internal_port, external_object, dst_element_label):
        for src_element in self.elements:
            if src_element.label == src_element_label:
                for dst_element in external_object:
                    if dst_element.label == dst_element_label:
                        src_element_label.add_connection(internal_port, dst_element)
                        return None
    
    
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


class Breaker(object):
    pass


class OverCurrentInstantaneousElement(object):
    def __init__(self, label, bus_to, bus_from, branch_data, branch_id, bus_data, I_max, interval):
        self.label = label
        self.interval = Decimal(str(interval))
        self.I_max = I_max
        self.bus_to_idx = bus_to
        self.bus_from_idx = bus_from
        self.bus_to_BaseKV = bus_data[bus_to, BASE_KV]
        self.bus_from_BaseKV = bus_data[bus_from, BASE_KV]
        self.R = branch_data[branch_id, BR_R] 
        self.X = branch_data[branch_id, BR_X]
        self.B = branch_data[branch_id, BR_B]
        self.ports = {"CMD_OPEN": False, "CMD_CLOSE": False}
        self.vars = {"I": None}
        self.current_state = "IDLE"
        self.connection = {}
        self.interval = Decimal(str(interval))

    def add_connection(self, internal_port, external_object):
        if internal_port in self.ports.keys():
            self.connection.update({internal_port: external_object})
            # self.connection[internal_port] = external_port_ref
    
    def step(self, vprev, events):
        print("State of the automaton {} before evalauting {}".format(
            self.label, self.current_state))
        if (self.current_state == "IDLE"):
            V1 = self.bus_to_BaseKV*np.abs(vprev[self.bus_to_idx])
            V2 = self.bus_from_BaseKV*np.abs(vprev[self.bus_from_idx])
            Y_series = np.abs(1/ (self.R + self.X))
            I =  (V1 - V2)* Y_series
            if (I > self.I_max):
                # print(I)
                self.current_state = "TRIPPED"
                self.ports["CMD_OPEN"] = True
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
            return self.interval
        else :
            print("No change in the state of automaton {}".format(self.label))
            return self.interval
    
    def update_interfaces(self):
        for internal_port in self.connection:
            self.connection[internal_port].ports[internal_port] = self.ports[internal_port]

             

class Breaker(object):
    def __init__(self, label, tto, ttc, interval, branch_id):
        self.label = label
        self.branch_id  = branch_id
        self.time = Decimal(0)
        self.tto = Decimal(str(tto))
        self.ttc = Decimal(str(ttc))
        self.interval = Decimal(str(interval))
        self.current_state = "CLOSED"
        self.ports = {"CMD_OPEN":False, "CMD_CLOSE": False}
        self.vars = {'timer':Decimal(0)}
        self.connection = {}

    def add_connection(self, external_port, internal_port):
        if internal_port in self.ports.keys():
            self.connection[internal_port] = external_port
    
    def step(self, vprev, events):
        print("State of the automaton {} before evalauting {}".format(
            self.label, self.current_state))
        self.time = self.time + self.interval
        if (self.current_state ==  "CLOSED"):
            if (self.ports["CMD_OPEN"]):
                self.ports["CMD_OPEN"] = False
                self.current_state = "OPENING"
                self.vars["timer"] = self.interval 
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                return self.interval
        elif (self.current_state == "OPENING"):
            if (self.vars['timer'] >= self.tto):
                self.current_state = "OPEN"
                self.vars["timer"] = 0
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                # Add TRIP Event Here
                events.event_stack.append([ self.time, "TRIP_BRANCH", self.branch_id])
                return self.interval
            else :
                print("No change in the state of the automaton {}".format(self.label))
                self.vars['timer'] =  self.vars["timer"] + self.interval
        elif (self.current_state == "OPEN"):
            if (self.ports["CMD_CLOSE"]):
                self.current_state = "CLOSING"
                self.ports["CMD_CLOSE"] = False
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                return self.interval
        else :
            if (self.vars["timer"] >= self.ttc):
                self.current_state = "CLOSED"
                self.vars["timer"] = 0
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                # Add ATTACH Event Here
                return self.interval
            else:
                print("No change in the state of the automaton {}".format(self.label))
                self.vars["timer"] = self.vars["timer"] + self.interval
        return self.interval
    
    def update_interfaces(self):
        for internal_port in self.connection:
            self.connection[internal_port] = self.ports[internal_port]