#!/usr/bin/python3

from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_restful.inputs import boolean
import argparse
import json
import os

def main(args):

    app = Flask(__name__)
    api = Api(app)

    req_parser_dict = reqparse.RequestParser()
    req_parser_dict.add_argument('parameters', required=True, help='configuration parameters for simulation')
    req_parser_conf = reqparse.RequestParser()
    req_parser_conf.add_argument('filename', required=True, help='name of the file')

    class WorkerEndPointDict(Resource):
        def post(self):
            req_args = req_parser_dict.parse_args()
            param = json.loads(req_args.parameters)
            return param

    class WorkerEndPointFile(Resource):
        def get(self):
            req_args = req_parser_conf.parse_args()
            # create a directory here
            dir = os.path.join(args.repo, hash(req_args.filename))
            os.makedirs(dir)
            return {'path':os.path.join(dir, req_args.filename)}
        def post(self):
            req_args = req_parser_conf.parse_args()
            if os.path.exists(req_args.filename):
                return {'message': 'Simulation will start soon'}
            else:
                return {'message': 'Configuration file missing, simulation will not start'}
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Power-Attack SImulation Worker End Point")
    parser.add_argument(
        "-p", "--port", help="Port to run this service", type=int, default=5000)
    parser.add_argument(
        "-r", "repo", help="Path to repo directory to save configuration files", 
        default=os.getcwd())
    args=parser.parse_args()
    print(args)
    main(args)
