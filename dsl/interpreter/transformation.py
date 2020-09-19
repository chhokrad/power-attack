#!/usr/local/bin/python3

import requests
import argparse
import pprint

from interpreter import Interpreter
from sampler import Sampler

def main(args):
    pp = pprint.PrettyPrinter(depth=2)
    power_attack_interpreter = Interpreter(args.meta_model)
    power_attack_interpreter.parse_sample_model(args.sample_model)
    # pp.pprint(power_attack_interpreter.preconditions)
    # print("="*150)
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
    
    
    for k in power_attack_sampler.params_list_with_scenario:
        print(k)
        for obj in power_attack_sampler.params_list_with_scenario[k]:
            print("=#="*50)
            pp.pprint(obj)
            print("=#="*50)
    # pp.pprint(power_attack_sampler.params_list_with_scenario)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Power-Attack CLI')
    parser.add_argument('-w', '--worker-config', 
                        help="conf. file listing collection of simulation worker end points",
                        default="/Users/ajaychhokra/projects/power-attack/worker/artifacts")
    parser.add_argument('-n', '--num-samples',
                        help= "number of samples",
                        default=10)
    parser.add_argument('-m', '--meta-model',
                        help="path to meta model or grammar",
                        default="/Users/ajaychhokra/projects/power-attack/dsl/grammar/attack.tx")
    parser.add_argument('-s', "--sample-model",
                        help="path to sample model",
                        default="/Users/ajaychhokra/projects/power-attack/dsl/sample-models/test1.atk")
    args = parser.parse_args()
    main(args)
