import json
import os
import warnings
import numpy as np
from copy import deepcopy

class Sampler(object):
    def __init__(self, params, breaker_params, relay_params, 
                controller_params, generator_params, simulation_params,
                preconditions, attack_scenarios, num_samples=10):
        self.params = params
        self.breaker_params = breaker_params
        self.relay_params = relay_params
        self.controller_params = controller_params
        self.generator_params = generator_params
        self.simulation_params = simulation_params
        self.preconditions = preconditions
        self.attack_scenarios = attack_scenarios
        self.num_samples = num_samples
        self.random_variables_samples = {}
        self.params_list = []
        self.params_list_with_scenario = {}

    def create_space(self):
        all_deterministic = self.check_probablistic_all()
        master_copy = { "breaker": self.breaker_params, 
                        "relay" : self.relay_params,
                        "controller": self.controller_params,
                        "generator": self.generator_params,
                        "simulation": self.simulation_params,
                        "preconditions": self.preconditions}
         
        if all_deterministic:
            self.params.update(master_copy)
            self.params_list.append(self.params)
        else:
            # TODO find a better way there is a lot of code repition
            a1 = self.create_breaker_param_space()
            a2 = self.create_relay_param_space()
            a3 = self.create_controller_param_space()
            a4 = self.create_generator_param_space()
            a5 = self.create_simulation_param_sapce()
            a6 = self.create_preconditions_space()

            for i in range(self.num_samples):
                self.params_list.append({   "breaker": a1[i], 
                                            "relay" : a2[i],
                                            "controller": a3[i],
                                            "generator": a4[i],
                                            "simulation": a5[i],
                                            "preconditions": a6[i]})
                self.params_list[i].update(self.params)
        # TODO this is difficult to understand and should be re-factored
        for scenario_label in self.attack_scenarios:
            scenario = self.attack_scenarios[scenario_label]
            flag = self.check_probablistic_list(scenario, scenario_label)
            if flag:
                params_list_copy = deepcopy(self.params_list)
                for params in params_list_copy:
                    params['sceanrio'] = scenario
                self.params_list_with_scenario[scenario_label] = params_list_copy
            else:
                params_list_copy = []
                if len(self.params_list) == 1:
                    for i in range(self.num_samples):
                        params_list_copy.append(deepcopy(self.params_list[0]))
                else:
                    params_list_copy = deepcopy(self.params_list)
                
                for index in range(len(params_list_copy)):
                    scenario_copy = deepcopy(scenario)
                    for var in self.random_variables_samples[scenario_label]:
                        index1, key = var.split('_')
                        index1 = int(index1)
                        scenario_copy[index1][key] = self.random_variables_samples[scenario_label][var][index]
                    params_list_copy[index]["scenario"] = scenario_copy
                self.params_list_with_scenario[scenario_label] = params_list_copy

    
    def create_breaker_param_space(self):
        space = []
        for ctr in range(self.num_samples):
            space.append(deepcopy(self.breaker_params))
        random_vars = self.random_variables_samples["breaker"]
        if len(random_vars) > 0:
            for key in random_vars:
                for index in range(len(space)):
                    space[index][key] = random_vars[key][index]
        return space


    def create_relay_param_space(self):
        space = []
        for ctr in range(self.num_samples):
            space.append(deepcopy(self.relay_params))
        random_vars = self.random_variables_samples["relay"]
        if len(random_vars) > 0:
            for key in random_vars:
                for index in range(len(space)):
                    sapce[index][key] = random_vars[key][index]
        return space

    def create_controller_param_space(self):
        space = []
        for ctr in range(self.num_samples):
            space.append(deepcopy(self.controller_params))
        random_vars = self.random_variables_samples["controller"]
        if len(random_vars) > 0:
            for key in random_vars:
                for index in range(len(space)):
                    sapce[index][key] = random_vars[key][index]
        return space

    def create_generator_param_space(self):
        space = []
        for ctr in range(self.num_samples):
            space.append(deepcopy(self.generator_params))
        random_vars = self.random_variables_samples["generator"]
        if len(random_vars) > 0:
            for key in random_vars:
                for index in range(len(space)):
                    sapce[index][key] = random_vars[key][index]
        return space
    
    def create_simulation_param_sapce(self):
        space = []
        for ctr in range(self.num_samples):
            space.append(deepcopy(self.simulation_params))
        random_vars = self.random_variables_samples["simulation"]
        if len(random_vars) > 0:
            for key in random_vars:
                for index in range(len(space)):
                    space[index][key] = random_vars[key][index]
        return space

    def create_preconditions_space(self):
        space = []
        for ctr in range(self.num_samples):
            space.append(deepcopy(self.preconditions))
        random_vars = self.random_variables_samples["preconditions"]
        if len(random_vars) > 0:
            for key in random_vars:
                index1, key1 = key.split('_')
                index1 = int(index1)
                for index in range(self.num_samples):
                    space[index][index1][key1] = random_vars[key][index]
        return space

    def create_attack_scenario_space(self, label):
        space_dict = {}

        return space_dict
    
    def check_probablistic_all(self):
        a = self.check_probablistic_dict(self.breaker_params, "breaker")
        b = self.check_probablistic_dict(self.relay_params, "relay")
        c = self.check_probablistic_dict(self.controller_params, "controller")
        d = self.check_probablistic_dict(self.generator_params, "generator")
        e = self.check_probablistic_dict(self.simulation_params, "simulation")
        f = self.check_probablistic_list(self.preconditions, "preconditions")
        return (a and b and c and d and e and f)

    def check_probablistic_list(self, params_list, label):
        # TODO find a bettwe way to identify probablistic values
        flag  =  True
        temp = {}
        for index in range(len(params_list)):
            element = params_list[index]
            for key in element:
                value = element[key]
                
                if value.__class__.__name__ == "tuple":
                    # its scalar
                    if value[0]:
                        samples = self.sample_value(value[1][0], value[1][1])
                        temp["{}_{}".format(index,key)] = samples
                        flag = False
                elif value.__class__.__name__ == "list":
                    if value[0][0] and not value[1][0]:
                        samples = self.sample_value(value[0][1][0], value[0][1][1])
                        samples_ = [(k, value[1][1]) for k in samples]
                        temp["{}_{}".format(index, key)] = samples_
                        flag = False
                    elif not value[0][0] and value[1][0]:
                        samples = self.sample_value(value[1][1][0], value[1][1][1])
                        samples_ = [(value[0][1], k) for k in samples]
                        temp["{}_{}".format(index, key)] = samples_
                        flag = False
                    elif value[0][0] and value[1][0]:
                        samples0 = self.sample_value(value[0][1][0], value[0][1][1])
                        samples1 = self.sample_value(value[1][1][0], value[1][1][1])
                        samples_ = list(zip(samples0, samples1))
                        temp["{}_{}".format(index, key)] = samples_
                        flag = False
                    else:
                        pass
                else:
                    pass
        self.random_variables_samples[label] = temp
        return flag
            

    def check_probablistic_dict(self, params, label):
        # TODO better way to find probablistic values
        flag = True
        temp = {}
        for key in params:
            value = params[key]
            if value.__class__.__name__ == "tuple":
                # its scalar
                if value[0]:
                    samples = self.sample_value(value[1][0], value[1][1])
                    temp[key] = samples
                    flag = False
            elif value.__class__.__name__ == "tuple":
                if value[0][0] and not value[1][0]:
                    samples = self.sample_value(value[0][1][0], value[0][1][1])
                    samples_ = [(k, value[1][1]) for k in samples]
                    temp[key] = samples_
                    flag = False
                elif not value[0][0] and  value[1][0]:
                    samples = self.sample_value(value[1][1][0], value[1][1][1])
                    samples_ = [(value[0][1], k) for k in samples]
                    temp[key] = samples_
                    flag = False
                elif value[0][0] and value[1][0]:
                    samples0 = self.sample_value(value[0][1][0], value[0][1][1])
                    samples1 = self.sample_value(value[1][1][0], value[1][1][1])
                    samples_ = list(zip(samples0, samples1))
                    temp[key] = samples_
                    flag = False
                else:
                    pass
            else:
                pass
        self.random_variables_samples[label] = temp
        return flag
    
    def sample_value(self, distribution, params): 
        # TODO make it generic
        samples = [1]*self.num_samples
        if distribution == "Uniform":
            low = params["low"][1]
            high = params["high"][1]
            samples = np.random.uniform(low, high, self.num_samples).tolist()
        elif distribution == "Discrete-Uniform":
            low = params["low"][1]
            high = params["high"][1]
            samples = np.random.randint(low, high, self.num_samples).tolist()
        elif distribution == "Gaussian":
            mue = params["mue"][1]
            sigma = params["sigma"][1]
            samples = np.random.normal(mue, sigma, self.num_samples).tolist()
        else:
            assert False, "Distribution type {} not supported yet".format(distribution)
        return samples
    

    




