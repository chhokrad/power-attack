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
from worker.simuator.pydyn.executor import Executor

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

    def get_distance_relay_params(self, from_bus, to_bus, branch_id):
        params = {}
        params['branch_id'] = branch_id
        params['to_bus'] = to_bus
        params['from_bus'] = from_bus
        params['ppc'] = self.ppc
        params['label'] = 'PA_DR_{}_{}'.format(from_bus, to_bus)

        for i in [1, 2, 3]:
            try:
                params['z{}_thresh'.format(
                    i)] = self.params['protection_system']['PA_DR_{}_{}'.format(
                        from_bus, to_bus)]['z{}_thresh'.format(i)]
            except KeyError:
                params['z{}_thresh'.format(
                    i)] = default_params['z{}_thresh'.format(i)]
            if i > 1:
                try:
                    params['z{}_delay'.format(
                        i)] = self.params['protection_system']['PA_DR_{}_{}'.format(
                            from_bus, to_bus)]['z{}_delay'.format(i)]
                except KeyError:
                    params['z{}_delay'.format(
                        i)] = default_params['z{}_delay'.format(i)]
        try:
            params['sampling_interval'] = self.params['protection_system']['PA_DR_{}_{}'.format(
                from_bus, to_bus)]['sampling_interval']
        except expression as identifier:
            params['sampling_interval'] = default_params['distance_relay_sampling_interval']

        return params

    def get_overload_relay_params(self, from_bus, to_bus, branch_id):
        params = {}
        params['branch_id'] = branch_id
        params['to_bus'] = to_bus
        params['from_bus'] = from_bus
        params['ppc'] = self.ppc
        params['label'] = 'PA_OR_{}_{}'.format(from_bus, to_bus)

        for i in [1, 2, 3]:
            try:
                params['o{}_thresh'.format(
                    i)] = self.params['protection_system']['PA_OR_{}_{}'.format(
                        from_bus, to_bus)]['o{}_thresh'.format(i)]
            except KeyError:
                params['o{}_thresh'.format(
                    i)] = default_params['o{}_thresh'.format(i)]

            try:
                params['o{}_delay'.format(
                    i)] = self.params['protection_system']['PA_OR_{}_{}'.format(
                        from_bus, to_bus)]['o{}_delay'.format(i)]
            except KeyError:
                params['o{}_delay'.format(
                    i)] = default_params['o{}_delay'.format(i)]
        try:
            params['sampling_interval'] = self.params['protection_system']['PA_OR_{}_{}'.format(
                from_bus, to_bus)]['sampling_interval']
        except expression as identifier:
            params['sampling_interval'] = default_params['overload_relay_sampling_interval']

        return params

    def get_breaker_params(self, from_bus, branch_id):
        params = {}
        params['branch_id'] = branch_id
        params['to_bus'] = to_bus
        params['from_bus'] = from_bus
        params['label'] = 'PA_BR_{}_{}'.format(from_bus, to_bus)

        try:
            params['tto'] = self.params['protection_system']['PA_BR_{}_{}'.format(
                from_bus, to_bus)]['tto']
        except KeyError:
            params['tto'] = default_params['tto']

        try:
            params['ttc'] = self.params['protection_system']['PA_BR_{}_{}'.format(
                from_bus, to_bus)]['ttc']
        except KeyError:
            params['ttc'] = default_params['ttc']

        try:
            params['sampling_interval'] = self.params['protection_system']['PA_BR_{}_{}'.format(
                from_bus, to_bus)]['sampling_interval']
        except expression as identifier:
            params['sampling_interval'] = default_params['breaker_sampling_interval']

        return params

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
            self.ppc['branch'] = np.vstack([self.ppc['branch'], new_branch_data])

    def generate_frequency_controllers(self):
        n = self.ppc['bus'].shape[0]
        n_gen = self.ppc['gen'].shape[0]

        node_id = [str(int(x-1)) for x in self.ppc['bus'][:, 0]]
        gen_id = [str(int(x-1)) for x in self.ppc['gen'][:, 0]]

        dest_dir = default_params['temporary_directory']
        H = default_params['H']
        alpha = [1.0 for x in H]
        k_consensus = [1/.16 for x in H]
        d_droop = [.05 for x in H]

        file_name_i = default_params['freq_ctr_filename']
        signals_ctrl_gen = default_params['signals_ctrl_gen']
        ctrl_dyn = default_params['ctrl_dyn']
        initialization = default_params['initialization']
        input_ctrl = default_params['input_ctrl']


        for i in range(n_gen):
            input_ctrl += "Omega_x = INPUT(Omega, freq_ctrlx)\n".replace('x', str(i))

        for i in range(n_gen):
            id_label = 'ID = freq_ctrl' + str(i) + '\n'
            input_ctrl_i = input_ctrl.replace('x', str(i))
            init = initialization.replace('d_droop', str(d_droop[i]))
            init = init.replace('alpha', str(alpha[i]))
            init = init.replace('k_consensus', str(k_consensus[i]))
            sec_ctrl_i = signals_ctrl_gen.replace(
                'x', str(i)) + input_ctrl_i + ctrl_dyn.replace('GENx', 'GEN'+str(i))
            file_name = dest_dir + '/' + file_name_i.replace('ith', str(i))
            with open(file_name, 'w') as f:
                f.write(id_label)
                f.write(header)
                f.write(sec_ctrl_i)
                f.write(init)

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
                    param_d1 = self.get_distance_relay_params(from_bus, to_bus, branch_id)
                    D1 = DistanceProtection(**param_d1)
                    
                    param_d2 = self.get_distance_relay_params(to_bus, from_bus, branch_id)
                    D2 = DistanceProtection(**param_d2)
                    
                    param_o1 = self.get_overload_relay_params(from_bus, to_bus, branch_id)
                    O1 = OverloadProtection(**param_o1)
                    
                    param_o2 = self.get_overload_relay_params(to_bus, from_bus, branch_id)
                    O2 = OverloadProtection(**param_o2)
                    
                    param_b1 = self.get_breaker_params(from_bus, to_bus, branch_id)
                    B1 = Breaker(**param_b1)
                    
                    param_b2 = self.get_breaker_params(to_bus, from_bus, branch_id)
                    B2 = Breaker(**param_b2)
                    
                    for i in [1, 2, 3]:
                        D1.add_connection("PA_DR_{}_{}_Z{}".format(from_bus, to_bus, i), "CMD_OPEN", B1)
                        O1.add_connection("PA_OR_{}_{}_O{}".format(from_bus, to_bus, i), "CMD_OPEN", B1)
                        D2.add_connection("PA_DR_{}_{}_Z{}".format(to_bus, from_bus, i), "CMD_OPEN", B2)
                        O2.add_connection("PA_OR_{}_{}_O{}".format(to_bus, from_bus, i), "CMD_OPEN", B2)

                    D1.add_connection("PA_DR_{}_{}_Z1", "TRIP_SEND",D2, "PA_DR_{}_{}_Z2", "TRIP_RECIEVE")
                    D2.add_connection("PA_DR_{}_{}_Z1", "TRIP_SEND",D1, "PA_DR_{}_{}_Z2", "TRIP_RECIEVE")
                    protection_devices.extend([D1, D2, O1, O2, B1, B2])
        
        self.ps_executor = Executor(protection_devices)

        # Setting up frequency controller
        self.generate_frequency_controllers(self.ppc)

        # Create Events file for physical events (Include precondition and attack scenarios)

        # Create event generator for cyber events (Include precondition and attack scenarios)

        # then implement the main function


    def run(self):
        run_sim(self.ppc, self.elements, self.dynopt,
                self.events, self.tracer, self.ps_executor)
