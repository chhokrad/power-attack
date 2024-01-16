#!python3

import numpy as np
from pdb import set_trace as bp


deg2rad = np.pi / 180
rad2deg = 180 / np.pi


# tolerance values for synchronize
omega_tol = 0.10
vm_tol = 0.01
delta_tol = 5


Tol = [omega_tol, vm_tol, delta_tol]

# time offeset for sync
#T_sync = 323
#T_sync = 350
T_sync = 100


def bound_angle(delta):
    return ((delta*180/np.pi + 180)%360) * np.pi/180 - np.pi


def rel_angle(omega, Vang, t):
    delta_omega = omega - 1
    return bound_angle( t*delta_omega*60*2*np.pi + Vang )


def in_sync(y):
    omega1 = y[0]
    omega2 = y[1]
    Vm1 = y[2]
    Vm2 = y[3]
    Vang1 = y[4]
    Vang2 = y[5]

    t = y[6]
    n_events = y[7]


    if t<T_sync or n_events <= 0:
        return 0.0

    omega_error = abs(omega1-omega2) * 60
    Vm_error = abs(Vm1-Vm2)

    Vang1_rel = rel_angle(omega1, Vang1, t)
    Vang2_rel = rel_angle(omega2, Vang2, t)
    #Vang_error = abs( Vang1_rel - Vang2_rel )
    Vang_error = abs(Vang1 - Vang2) * rad2deg

    if ((omega_tol) >= omega_error) and (Vm_error <= vm_tol) and (Vang_error <= (delta_tol)) :
        return 1.0
    else:
        return 0.0
