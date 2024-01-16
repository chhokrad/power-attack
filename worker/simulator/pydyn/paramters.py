import os
from pathlib import Path

file_path = os.path.abspath(__file__)
dir = Path(file_path).parents[2]
art_dir = os.path.join(dir, 'artifacts')
if not os.path.isdir(art_dir):
    os.makedirs(art_dir)

default_params = {
"artifacts": art_dir,
"dynamic_simulation_parameters": {

    'h' : 0.001,
    'sample_period' : 0.01,
    't_sim' : 10,
    'max_err' : 1e-8,
    'max_iter' : 60,
    'verbose' : False,
    'fn' : 60,
    'speed_volt' : True,
    'iopt' : 'runge_kutta'},

'header': '''

##########################
# define the signals
''',

'freq_ctr_filename': 'freq_ctrlith.dyn',
    
'signals_ctrl_gen': '''

Pm_ref = REF()
omega_ref = REF()
# used for initialization
Pm0 = INPUT(Pm,GENx)
Pm_droop = REF()
Omega = REF()
Omega_local = REF()

''',
    
    
'ctrl_dyn': '''

call_func = INT_FUNC(update_ctrl.freq)
Omega_nom = INT(Omega_dot, K, 1)
Omega_local = MULT(Omega_nom, 1)
u = SUM(Pm_droop, Omega_local)
Pm_tot = SUM(Pm_ref, u) 
Pm = OUTPUT(Pm_tot, GENx)

''',
    
'initialization': '''

##################
# Initialisation #
##################

INIT
SIGNAL = D = CONST(d_droop)
SIGNAL = Alpha = CONST(alpha)
SIGNAL = K = CONST(k_consensus)
SIGNAL = Pm_ref = MULT(Pm0, 1)
SIGNAL = omega_ref = CONST(1.0)
SIGNAL = attack_scale = CONST(1.0)
SIGNAL = attack_bias = CONST(0.0)
#SIGNAL = max_droop = CONST(max_droop**)

''',
    
'input_ctrl': '''

# frequency in the generator
gen = INPUT(gen, sys_matrices)
omega = INPUT(omega,GENx)
omega_error = SUM(omega_ref, -omega)

# Control variables

''',

    'sync.dyn': '''

ID = SYNC1

#########################
# Controller Definition #
#########################

omega1 = INPUT(omega,GEN1)
omega2 = INPUT(omega,GEN2)

omega_error = SUM(omega1, -omega2)


Vang5 = INPUT(Va4,bus)
Vang7 = INPUT(Va6,bus)

Vang_error = SUM(Vang5, -Vang7)


Vm5 = INPUT(Vm4,bus)
Vm7 = INPUT(Vm6,bus)

Vm_error = SUM(Vm5, -Vm7)


t = INT(k, 1, 1)
N_events = REF()


sync = FUNC(sync.in_sync, omega1, omega2, Vm5, Vm7, Vang5, Vang7, t, N_events)

event = EVENT(sync, ENABLE_BRANCH, 7)
event = EVENT(sync, SIGNAL, AVR1, select, 1.0)
event = EVENT(sync, SIGNAL, AVR2, select, 1.0)
N_events = SUM(N_events, -event)






##################
# Initialisation #
##################

INIT
SIGNAL = omega_ref = CONST(1.0)
SIGNAL = k = CONST(1.0)
SIGNAL = N_events = CONST(0.0)
    ''',

'z1_thresh' : 24,
'z2_thresh' : 25,
'z3_thresh' : 26,
'z2_delay'  : 0.1,
'z3_delay'  : 1.5,
'relay_sampling_interval' : 0.008,
'i1_thresh' : 200,
'i2_thresh' : 400,
'i3_thresh' : 600,
'i1_delay'  : 300,
'i2_delay'  : 600,
'i3_delay'  : 1200,
'breaker_sampling_interval' : 0.004,
'tto'   : 0.090,
'ttc'   : 0.090

}
