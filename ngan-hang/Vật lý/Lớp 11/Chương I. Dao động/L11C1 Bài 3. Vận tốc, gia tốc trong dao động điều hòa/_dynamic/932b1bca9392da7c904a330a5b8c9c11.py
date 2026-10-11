import math
import random

def sinh_so_lieu():
    he_so_vmax = random.randint(2, 15)
    he_so_omega = random.randint(1, 10)
    return {'he_so_vmax': he_so_vmax, 'he_so_omega': he_so_omega}

def tinh_cau_78(he_so_vmax, he_so_omega):
    return he_so_vmax*he_so_omega*10
