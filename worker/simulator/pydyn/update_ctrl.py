# control function

import numpy as np
from pdb import set_trace as bp

def freq(id_ctrl, signals):
    print(signals)
    gen_id = int(id_ctrl.replace('freq_ctrl', ''))
    
    # primary ctrl
    freq_error = signals['omega_ref'] - signals['omega']

    signals['Pm_droop'] = signals['D']*freq_error


    n_gen = signals['gen'].shape[0]

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

    Omega = np.zeros(n_gen)
    for i in range(n_gen):
        Omega[i] = signals['Omega_'+str(i)] 

    
    # the scale attack changes the local variable
    Omega[gen_id] = signals['Omega_local'] * signals['attack_scale'] 

    # the bias attack changes the global variables (this value isn't used by the control)
    signals['Omega'] = Omega[gen_id] + signals['attack_bias']


    d_ij = np.ones(n_gen)
    for j in range(n_gen):
        d_ij[j] = Omega[gen_id] - Omega[j]

    w = np.zeros(n_gen)
    for j in range(n_gen):
        w[j] = com_net[gen_id, j] * d_ij[j]

    signals['Omega_dot'] = freq_error * signals['Alpha'] - sum(w)

    return signals





def freq_resilient(id_ctrl, signals):
    gen_id = int(id_ctrl.replace('freq_ctrl', ''))
    
    # primary ctrl
    freq_error = signals['omega_ref'] - signals['omega']

    signals['Pm_droop'] = signals['D']*freq_error

    n_gen = signals['gen'].shape[0]

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

        # get the list of neighbors
        N = []
        index_gen = -1
        for j in range(n_gen):
            if com_net[gen_id, j] != 0:
                N.append(j)
                if j == gen_id:
                    index_gen = len(N)-1

    Omega = []
    for j in N:
        Omega_j = signals['Omega_'+str( j )]
        Omega.append( Omega_j )

    index_sorted = sorted(range(len(Omega)), key=Omega.__getitem__)

    # find the lower and upper index to reduce the vector
    k = 0
    while k < signals['max_droop']:
        if index_sorted[k] == index_gen:
            break
        else:
            k+=1
    lower_pos = k

    k = 0
    while k < signals['max_droop']:
        if index_sorted[len(N)-k-1] == index_gen:
            break
        else:
            k+=1
    upper_pos = len(N)-k

    Omega_cut = []
    for k in index_sorted[lower_pos:upper_pos]:
        if k != index_gen:
            Omega_cut.append( Omega[k] )


    # the scale attack changes the local variable
    Omega_i = signals['Omega_local'] * signals['attack_scale'] 


    d_ij = []
    for Omega_j in Omega_cut:
        d_ij.append( Omega_i - Omega_j )

    signals['Omega_dot'] = freq_error * signals['Alpha'] - sum( d_ij )


    # the bias attack changes the global variables
    signals['Omega'] = Omega_i + signals['attack_bias']

    #bp()

    return signals






def volt(id_ctrl, signals):
    gen_id = int(id_ctrl.replace('sec_volt_ctrl', ''))
    
    # primary ctrl
    signals['Vt_error'] = signals['Vt_ref'] - signals['Vt']
    signals['Q_error'] = signals['Q_ref'] - signals['Q']

    signals['Q_droop'] = signals['D']*signals['Q_error']

    # secondary control
    n_gen = signals['gen'].shape[0]

    gamma = 0.0

    Q = np.zeros(n_gen)
    for i in range(n_gen):
        Q[i] = signals['Q'+str(i)] 

    d_ij = np.ones(n_gen)
    for j in range(n_gen):
        d_ij[j] = Q[gen_id] - Q[j]

    w = np.zeros(n_gen)
    for j in range(n_gen):
        w[j] = com_net[gen_id, j] * d_ij[j] * gamma

    signals['e_dot'] = signals['beta']*signals['Vt_error'] - sum(w)

    signals['E_i'] = signals['Vt_ref'] + signals['Q_droop'] + signals['e']

    return signals
