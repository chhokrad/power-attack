from worker.simuator.pydyn.controller import controller
from worker.simuator.pydyn.sym_order6a import sym_order6a
from worker.simuator.pydyn.sym_order6b import sym_order6b
from worker.simuator.pydyn.sym_order4 import sym_order4
from worker.simuator.pydyn.ext_grid import ext_grid

from worker.simuator.pydyn.events import events
from worker.simuator.pydyn.recorder import recorder
from worker.simuator.pydyn.run_sim import run_sim

from pypower.loadcase import loadcase
from pypower.idx_bus import *
from pypower.idx_brch import *

from worker.simuator.pydyn.protection import DistanceProtection
from worker.simuator.pydyn.protection import OverloadProtection
from worker.simuator.pydyn.protection import Breaker

import matplotlib.pyplot as plt
import numpy as np
from worker.simuator.pydyn.paramters import default_params
from copy import deepcopy
import warnings

class SimulatorPyDyn(object):
    def __init__(self, params):
        self.params = params
        self.dynopt = deepcopy(default_params)
        self.branch_pseudo_bus_map = {}

    def get_distance_relay_params(self, branch_id, from_bus, to_bus):
        pass

    def get_overload_relay_params(self, branch_id, from_bus, to_bus):
        pass

    def get_breaker_params(self, branch_id, from_bus, to_bus):
        pass

    def add_pseudo_buses(self, branch_ids):
        for branch_id in branch_ids:
            branch_data = self.ppc['branch'][branch_id, :]
            to_bus = int(branch_data[T_BUS])  # external numbering
            from_bus = int(branch_data[F_BUS])  # external numbering
            # TODO find a better way to convert external to internal
            if self.ppc['bus'][to_bus-1, BASE_KV] != self.ppc['bus'][from_bus-1, BASE_KV]:
                warnings.warn(
                    "Cannot inject fault in branch between {} and {}".format(to_bus, from_bus))
                continue
            bus_id_max = int(max([x[BUS_I] for x in self.ppc['bus']]))
            new_bus_id = bus_id_max + 1
            new_bus_data = deepcopy(self.ppc['bus'][from_bus-1, :])
            new_bus_data[BUS_I] = new_bus_id
            new_bus_data[BUS_TYPE] = PQ
            for idx in [PD, QD, GS, BS]:
                new_bus_data[idx] = 0
            self.ppc['bus'] = np.vstack([self.ppc['bus'], new_bus_data])
            self.branch_pseudo_bus_map[branch_id] = new_bus_id
            branch_data[BR_R] = branch_data[BR_R]/2
            branch_data[BR_X] = branch_data[BR_X]/2
            branch_data[BR_B] = branch_data[BR_B]/2
            new_branch_data = deepcopy(branch_data)
            branch_data[T_BUS] = new_bus_id
            new_branch_data[F_BUS] = new_bus_id
            self.ppc['branch'] = np.vstack([ppc['branch'], new_branch_data])

    def setup(self):
        simulation_parameters = self.params['simulation']
        for param in simulation_parameters:
            if param in self.dynopt.keys():
                self.dynopt[param] = simulation_parameters[param]
            else:
                warnings.warn("Ignoring parameter {}".format(param))

        # Configuration parameters
        self.ppc = loadcase(self.dynopt['case'])
        # Store preconditions in a list
        self.event_list = self.params['precondition']
        # precondition key's value is a list  where each elememt is a dictionary
        # keys are time, type, value
        # value is an dictionary that is specific to the event type
        pseudo_buses_to_be_added = []
        for event in self.event_list:
            if 'FAULT' in event:
                pseudo_buses_to_be_added.append(event['value']['branch'])
        self.add_pseudo_buses(pseudo_buses_to_be_added)
        # Set up protection system with default settings

        protection_devices = []

        for branch_id in range(0, len(self.ppc['branch'])):
            # check if its a transmission line
            if self.ppc['branch'][branch_id, BR_B] != 0 or self.ppc['branch'][branch_id, BR_R] != 0:
                to_bus = int(self.ppc['branch'][branch_id, T_BUS])
                from_bus = int(self.ppc['branch'][branch_id, F_BUS])
                if self.ppc['bus'][to_bus-1, BASE_KV] == self.ppc['bus'][from_bus-1, BASE_KV]:
                    D1 = DistanceProtection(0.8, 1.25, 2, 5*0.016, 100*0.016,
                                            "PA_DR_{}_{}".format(
                                                from_bus, to_bus),
                                            self.ppc, 0.01, to_bus, from_bus, branch_id)
                    O1 = OverloadProtection(2, 5, 10, 10000*0.016, 5000*0.016, 1000*0.016,
                                            "PA_OR_{}_{}".format(
                                                from_bus, to_bus),
                                            self.ppc, 0.01, to_bus, from_bus, branch_id)
                    D2 = DistanceProtection(0.8, 1.25, 2, 5*0.016, 100*0.016,
                                            "PA_DR_{}_{}".format(
                                                to_bus, from_bus),
                                            self.ppc, 0.01, from_bus, to_bus, branch_id)
                    O2 = OverloadProtection(2, 5, 10, 10000*0.016, 5000*0.016, 1000*0.016,
                                            "PA_OR_{}_{}".format(
                                                to_bus, from_bus),
                                            self.ppc, 0.01, from_bus, to_bus, branch_id)
                    B1 = Breaker("PA_BR_{}_{}".format(from_bus, to_bus),
                                 0.001, 5*0.016, 5*0.016, branch_id)
                    B2 = Breaker("PA_BR_{}_{}".format(to_bus, from_bus),
                                 0.001, 5*0.016, 5*0.016, branch_id)
                    for i in [1, 2, 3]:
                        D1.add_connection("PA_DR_{}_{}_Z{}".format(
                            from_bus, to_bus, i), "CMD_OPEN", B1)
                        O1.add_connection("PA_OR_{}_{}_O{}".format(
                            from_bus, to_bus, i), "CMD_OPEN", B1)
                        D2.add_connection("PA_DR_{}_{}_Z{}".format(
                            to_bus, from_bus, i), "CMD_OPEN", B2)
                        O2.add_connection("PA_OR_{}_{}_O{}".format(
                            to_bus, from_bus, i), "CMD_OPEN", B2)
                    
                    D1.add_connection("PA_DR_{}_{}_Z1", "TRIP_SEND", 
                                    D2, "PA_DR_{}_{}_Z2", "TRIP_RECIEVE")
                    D2.add_connection("PA_DR_{}_{}_Z1", "TRIP_SEND",
                                      D1, "PA_DR_{}_{}_Z2", "TRIP_RECIEVE")
                    protection_devices.extend([D1, D2, O1, O2, B1, B2])
                
        
        
        # Update protection system with protection system parameters
        # Parameters for breaker: tto, ttc, sampling interval
        # Parameters for instantaneous element: threhold
        # Parameters for timedelayed element: delay, threshold
        # Set up frequency controller
        # Set up recorder through sqlite

        # Precondition parameters
        # Create an event file

        # Attack scenarios
        # Update the event file based on attack sequence

    def run(self):
        run_sim(self.ppc, self.elements, self.dynopt,
                self.events, self.tracer, self.ps_executor)
