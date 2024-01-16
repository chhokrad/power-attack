import numpy as np
from pypower.loadcase import loadcase

ppc = loadcase('../grid_models/'+case)


n = ppc['bus'].shape[0]
n_gen = ppc['gen'].shape[0]

node_id = [str(int(x)) for x in ppc['bus'][:, 0]]


# select the type of communication graph between the generators
graph=2

if graph == 0:
    # connected graph
    com_net = np.ones((n_gen, n_gen))

elif graph == 1:
    # simple graph
    com_net = np.zeros((n_gen, n_gen))
    for i in range(n_gen-1):
        j = i+1
        com_net[i, j] = 1
    com_net[0, n_gen-1] = 1
    com_net = com_net + com_net.T

elif graph == 2:
    # isolated nodes
    com_net = np.zeros((n_gen, n_gen))
    for i in range(n_gen):
        com_net[i, i] = 1
