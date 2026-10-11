import math
import random

def sinh_so_lieu():
    he_so_vmax = random.randint(1, 8) * 5
    amax = random.randint(1, 10)
    return {'he_so_vmax': he_so_vmax, 'amax': amax}

def tinh_cau_107(he_so_vmax, amax):
    return (he_so_vmax**2*10/(100*amax),2*he_so_vmax*10/(100*amax))
