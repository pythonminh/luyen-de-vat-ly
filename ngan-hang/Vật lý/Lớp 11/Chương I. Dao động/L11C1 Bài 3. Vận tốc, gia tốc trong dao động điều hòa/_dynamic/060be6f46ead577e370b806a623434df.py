import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 12)
    vmax = bien_do * random.randint(1, 10)
    return {'vmax': vmax, 'bien_do': bien_do}

def tinh_L11C1B3_35_TLN(vmax, bien_do):
    return vmax/bien_do
