import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 15)
    he_so_vmax = random.randint(2, 20)
    return {'bien_do': bien_do, 'he_so_vmax': he_so_vmax}

def tinh_cau_119(bien_do, he_so_vmax):
    return 2*bien_do/he_so_vmax
