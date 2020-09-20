
from worker.simulator.pydyn.controller import controller
from worker.simulator.pydyn.sym_order6a import sym_order6a
from worker.simulator.pydyn.sym_order6b import sym_order6b
from worker.simulator.pydyn.sym_order4 import sym_order4
from worker.simulator.pydyn.ext_grid import ext_grid

from worker.simulator.pydyn.events import events
from worker.simulator.pydyn.recorder import recorder
from worker.simulator.pydyn.run_sim import run_sim

from pypower.loadcase import loadcase
from pypower.idx_bus import *
from pypower.idx_brch import *

from worker.simulator.pydyn.protection import DistanceProtection
from worker.simulator.pydyn.protection import OverloadProtection
from worker.simulator.pydyn.protection import Breaker
from worker.simulator.pydyn.executor import Executor
from worker.simulator.pydyn.protection import EventInjector

import matplotlib.pyplot as plt
import numpy as np
from worker.simulator.pydyn.paramters import default_params
from copy import deepcopy
import warnings
import os


class SimulatorPyDyn(object):
    def __init__(self, params):
        self.params = params
        self.dynopt = {}
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
            self.ppc['branch'] = np.vstack(
                [self.ppc['branch'], new_branch_data])

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
            input_ctrl += "Omega_x = INPUT(Omega, freq_ctrlx)\n".replace(
                'x', str(i))

        for i in range(n_gen):
            id_label = 'ID = freq_ctrl' + str(i) + '\n'
            input_ctrl_i = input_ctrl.replace('x', str(i))
            init = initialization.replace('d_droop', str(d_droop[i]))
            init = init.replace('alpha', str(alpha[i]))
            init = init.replace('k_consensus', str(k_consensus[i]))
            sec_ctrl_i = signals_ctrl_gen.replace(
                'x', str(i)) + input_ctrl_i + ctrl_dyn.replace('GENx', 'GEN'+str(i))
            file_name = os.path.join(
                dest_dir, file_name_i.replace('ith', str(i)))
            # file_name = dest_dir + '/' + file_name_i.replace('ith', str(i))
            with open(file_name, 'w') as f:
                f.write(id_label)
                f.write(header)
                f.write(sec_ctrl_i)
                f.write(init)

    def setup(self):
        simulation_parameters = self.params['dynamic_simulation_parameters'] 
        for param in default_params['dynamic_simulation_parameters']:
            if param in simulation_parameters:
                self.dynopt[param] = simulation_parameters[param]
            else:
                self.dynopt[param] = default_params['dynamic_simulation_parameters'][param]
        
        # Configuration parameters
        self.ppc = loadcase(self.dynopt['case'])
        # Setting up frequency controllers
        self.generate_frequency_controllers(self.ppc)
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
                    param_d1 = self.get_distance_relay_params(
                        from_bus, to_bus, branch_id)
                    D1 = DistanceProtection(**param_d1)

                    param_d2 = self.get_distance_relay_params(
                        to_bus, from_bus, branch_id)
                    D2 = DistanceProtection(**param_d2)

                    param_o1 = self.get_overload_relay_params(
                        from_bus, to_bus, branch_id)
                    O1 = OverloadProtection(**param_o1)

                    param_o2 = self.get_overload_relay_params(
                        to_bus, from_bus, branch_id)
                    O2 = OverloadProtection(**param_o2)

                    param_b1 = self.get_breaker_params(
                        from_bus, to_bus, branch_id)
                    B1 = Breaker(**param_b1)

                    param_b2 = self.get_breaker_params(
                        to_bus, from_bus, branch_id)
                    B2 = Breaker(**param_b2)

                    for i in [1, 2, 3]:
                        D1.add_connection("PA_DR_{}_{}_Z{}".format(
                            from_bus, to_bus, i), "CMD_OPEN", B1)
                        O1.add_connection("PA_OR_{}_{}_O{}".format(
                            from_bus, to_bus, i), "CMD_OPEN", B1)
                        D2.add_connection("PA_DR_{}_{}_Z{}".format(
                            to_bus, from_bus, i), "CMD_OPEN", B2)
                        O2.add_connection("PA_OR_{}_{}_O{}".format(
                            to_bus, from_bus, i), "CMD_OPEN", B2)

                    D1.add_connection(
                        "PA_DR_{}_{}_Z1", "TRIP_SEND", D2, "PA_DR_{}_{}_Z2", "TRIP_RECIEVE")
                    D2.add_connection(
                        "PA_DR_{}_{}_Z1", "TRIP_SEND", D1, "PA_DR_{}_{}_Z2", "TRIP_RECIEVE")
                    protection_devices.extend([D1, D2, O1, O2, B1, B2])

        # Create Events file for physical events (Include precondition and attack scenarios)
        attack_sequence = []
        if "attack scenario" in self.params.keys():
            attack_sequence = self.params["attack_scenario"]

        # attack sequence is a sequence where each component is
        # an attack can be a scaling and biasing attack : Generator Attack
        # an attack can be a SPURIOUS and MISSED detection attack on a branch : Relay Attack
        # an attack can be a STUCK OPEN or STUCK CLOSE attack on a braker : Breaker Attack
        generator_attack = []
        protection_system_attack = []
        for attack in attack_sequence:
            if attack['type'] == "Relay" or attack['type'] == "Breaker":
                protection_system_attack.append(attack)
            else:
                generator_attack.append(attack)

        if len(generator_attack) > 0:
            self.event_list.extend(generator_attack)

        if len(protection_system_attack) > 0:
            event_injector = EventInjector()
            event_injector.add_events(
                protection_system_attack, protection_devices, self.dynopt['h'])
            protection_devices.insert(0, event_injector)

        self.ps_executor = Executor(protection_devices)

        # Create event file for physical events
        # Only supported events here are LOAD, FAULT, SIGNAL
        # event list with time
        self.event_list = sorted(self.event_list, key=lambda k: k['time'])
        dest_dir = default_params['temporary_directory']
        event_file = os.path.join(dest_dir, 'event.evnt')
        with open(event_file, 'w') as eventfile:
            for event in self.event_list:
                if event["type"] == "LOAD":
                    # 1.0, LOAD, 0, 80, 30
                    eventfile.write("{}, LOAD, {}, {}, {}".format(event["time"],
                                                                  event["value"]["bus"],
                                                                  event["value"]["Pd"],
                                                                  event["value"]["Qd"]))
                elif event["type"] == "FAULT":
                    #1.0, FAULT, 16, 0.5, 0.5
                    # TODO Need better internal numbering mechanism
                    bus = self.branch_pseudo_bus_map[event["value"]
                                                     ["branch"]] - 1
                    eventfile.write("{}, FAULT, {}, {}, {}".format(event["time"],
                                                                   bus, 0, 0))

                elif event["type"] == "SCALE":
                    # 160.0, SIGNAL, freq_ctrl0, attack_bias, 0.01
                    n_gen = self.ppc['gen'].shape[0]
                    gen_no = None
                    for n in range(n_gen):
                        if self.ppc['gen'][n, 0] == event["value"]["bus"]:
                            n_gen = n
                            break
                    if n_gen is not None:
                        eventfile.write("{}, SIGNAL, freq_ctrl{}, attack_scale, {}".format(
                            event["time"],
                            gen_no,
                            event["value"]
                        ))

                elif event["type"] == "BIAS":
                    n_gen = self.ppc['gen'].shape[0]
                    gen_no = None
                    for n in range(n_gen):
                        if self.ppc['gen'][n, 0] == event["value"]["bus"]:
                            n_gen = n
                            break
                    if n_gen is not None:
                        eventfile.write("{}, SIGNAL, freq_ctrl{}, attack_bias, {}".format(
                            event["time"],
                            gen_no,
                            event["value"]
                        ))

                else:
                    warnings.warn(
                        "Event {} not supported as of now".format(event["type"]))

            eventfile.close()

        self.elements = {}
        for i in range(n_gen):
            #G_i = sym_order6b('Generator'+ str(i) +'.mach', dynopt)
            G_i = ext_grid('GEN'+str(i), i, 0.1198, H[i], self.dynopt)
            self.elements[G_i.id] = G_i
            freq_ctrl_i = controller('freq_ctrl' + str(i) + '.dyn', self.dynopt)
            self.elements[freq_ctrl_i.id] = freq_ctrl_i

        # TODO correct path to sync.dyn
        sync1 = controller('sync.dyn', dynopt)
        self.elements[sync1.id] = sync1
        self.events = events(event_file)


    def setup_and_run(self):
        self.setup()
        run_sim(self.ppc, self.elements, self.dynopt,
                self.events, self.tracer, self.ps_executor)