#!/usr/local/bin/python3

import requests
import argparse

from dsl.interpreter.interpreter import Interpreter
from dsl.interpreter.sampler import Sampler

def main(args):
    pass

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
    print(args)
    main(args)
