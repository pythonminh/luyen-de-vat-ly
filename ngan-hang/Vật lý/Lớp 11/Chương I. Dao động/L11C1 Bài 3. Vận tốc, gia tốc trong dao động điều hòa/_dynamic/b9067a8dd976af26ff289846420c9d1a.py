import math
import random

def sinh_so_lieu():
    vmax = random.randint(10, 50)
    amax = vmax * random.randint(1, 10)
    li_do = vmax**2/amax * random.choice([0.2, 0.4, 0.6, 0.8])
    return {'vmax': vmax, 'amax': amax, 'li_do': li_do}

def tinh_L11C1B3_34_TN(vmax, amax, li_do):
    return math.sqrt(vmax**2-(amax/vmax*li_do)**2)
