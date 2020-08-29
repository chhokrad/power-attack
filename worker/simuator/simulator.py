from pydyn.controller import controller
from pydyn.sym_order6a import sym_order6a
from pydyn.sym_order6b import sym_order6b
from pydyn.sym_order4 import sym_order4
from pydyn.ext_grid import ext_grid

from pydyn.events import events
from pydyn.recorder import recorder
from pydyn.run_sim import run_sim

from pypower.loadcase import loadcase
import matplotlib.pyplot as plt
import numpy as np



class Simulator(object):
    def __init__(self, params):
        self.params = self.get_params(params)
    
    def setup(self):
        self.ppc = loadcase('../grid_models/'+ self.params['case'])
        n = self.ppc['bus'].shape[0]
        n_gen = self.ppc['gen'].shape[0]
        n_branch = self.ppc['branch'].shape[0]
        self.dynopt = {}
        self.dynopt['h'] = 0.001                
        self.dynopt['sample_period'] = 0.01
        self.dynopt['t_sim'] = self.params['t_sim']           
        self.dynopt['max_err'] = 1e-8
        self.dynopt['max_iter'] = 60           
        self.dynopt['verbose'] = False         
        self.dynopt['fn'] = 60                 
        self.dynopt['speed_volt'] = True
        self.dynopt['iopt'] = 'runge_kutta'
        self.elements = {}
        for i in range(n_gen):
            G_i = ext_grid('GEN'+str(i), i, self.params['Xdp'][i], self.params['H'][i], self.dynopt)
            self.elements[G_i.id] = G_i
            freq_ctrl_i = controller('freq_ctrl' + str(i) + '.dyn', self.dynopt)
            self.elements[freq_ctrl_i.id] = freq_ctrl_i
        
        sync1 = controller('sync.dyn', self.dynopt)
        self.elements[sync1.id] = sync1

        self.events = events('events.evnt')


    def run(self):
        run_sim(self.ppc, self.elements, self.dynopt, self.events, self.tracer, self.ps_executor)
