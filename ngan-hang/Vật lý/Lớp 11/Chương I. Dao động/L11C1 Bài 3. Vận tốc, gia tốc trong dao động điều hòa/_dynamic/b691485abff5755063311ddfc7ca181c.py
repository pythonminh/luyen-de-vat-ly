import math
import random

def sinh_so_lieu():
    bien_do = random.randint(5, 15)
    vmax = bien_do * random.randint(1, 10)
    li_do = bien_do * random.choice([0.2, 0.4, 0.6, 0.8])
    return {'bien_do': bien_do, 'vmax': vmax, 'li_do': li_do}

def tinh_cau_80(bien_do, vmax, li_do):
    return vmax/bien_do*math.sqrt(bien_do**2-li_do**2)
