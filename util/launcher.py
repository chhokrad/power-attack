#!/usr/bin/env python3

import requests
import argparse
import pprint
import os
from dsl.interpreter.interpreter import Interpreter
from dsl.interpreter.sampler import Sampler
import multiprocessing
from worker.simulator.simulator import SimulatorPyDyn
from multiprocessing import Pool
from time import sleep


NUM_CORES = multiprocessing.cpu_count()
pp = pprint.PrettyPrinter(depth=3)

def start_simulation(args, id):
    # pp.pprint(args)
    sim = SimulatorPyDyn(args, id)
    sim.setup_and_run()


def main(args):
    
    power_attack_interpreter = Interpreter(args.meta_model)
    power_attack_interpreter.parse_sample_model(args.sample_model)
    power_attack_sampler = Sampler(power_attack_interpreter.params,
                                    power_attack_interpreter.breaker_params,
                                    power_attack_interpreter.relay_params,
                                    power_attack_interpreter.controller_params,
                                    power_attack_interpreter.generator_params,
                                    power_attack_interpreter.simulation_params,
                                    power_attack_interpreter.preconditions,
                                    power_attack_interpreter.attack_scenarios,
                                    args.num_samples)
    power_attack_sampler.create_space()
    
    
    if args.worker_config is not None:
        # run remotely
        pass
    else:
        # run locally
        # configs = []
        # for scenario in power_attack_sampler.params_list_with_scenario:
        #     for params_dict in power_attack_sampler.params_list_with_scenario[scenario]:
        #         configs.append(params_dict)
        # worker_pool = Pool(args.num_processes)
        # worker_pool.map(start_simulation, configs)
        start_simulation(power_attack_sampler.params_list_with_scenario["Scenario1"][0], "test123")




if __name__ == "__main__":
    repo_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_src)
    parser = argparse.ArgumentParser(description='Power-Attack CLI')
    parser.add_argument('-w', '--worker-config', 
                        help="conf. file listing collection of simulation worker end points")
    parser.add_argument('-n', '--num-samples',
                        help= "number of samples",
                        default=10)
    parser.add_argument('-m', '--meta-model',
                        help="path to meta model or grammar",
                        default="dsl/grammar/attack.tx")
    parser.add_argument('-s', "--sample-model",
                        help="path to sample model",
                        default="dsl/sample-models/test1.atk")
    parser.add_argument('-p', "--num-processes",
                        help="Number of local processes",
                        type=int,
                        default=NUM_CORES)
    args = parser.parse_args()
    main(args)
