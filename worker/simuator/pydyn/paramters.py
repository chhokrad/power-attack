default_params = {
"case" : "case39",
'h' : 0.001,
'sample_period' : 0.01,
't_sim' : 10,
'max_err' : 1e-8,
'max_iter' : 60,
'verbose' : False,
'fn' : 60,
'speed_volt' : True,
'iopt' : 'runge_kutta',
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
    'initialization': ''''

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
SIGNAL = max_droop = CONST(max_droop**)

''',
    'input_ctrl': '''

# frequency in the generator
gen = INPUT(gen, sys_matrices)
omega = INPUT(omega,GENx)
omega_error = SUM(omega_ref, -omega)

# Control variables

'''
}
