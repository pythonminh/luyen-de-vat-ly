import math
import random

def sinh_so_lieu():
    he_so_vmax = random.randint(2, 15)
    he_so_amax = random.randint(2, 30)
    return {'he_so_vmax': he_so_vmax, 'he_so_amax': he_so_amax}

def tinh_L11C1B3_28_TN(he_so_vmax, he_so_amax):
    return he_so_vmax**2/he_so_amax
