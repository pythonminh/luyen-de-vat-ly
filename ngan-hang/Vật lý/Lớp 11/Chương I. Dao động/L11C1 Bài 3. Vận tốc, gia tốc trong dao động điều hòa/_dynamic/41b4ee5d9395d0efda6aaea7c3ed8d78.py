import math
import random

def sinh_so_lieu():
    bien_do = random.randint(5, 15)
    vmax = bien_do * random.randint(1, 10)
    toc_do = vmax * random.choice([0.2, 0.4, 0.6, 0.8])
    return {'bien_do': bien_do, 'vmax': vmax, 'toc_do': toc_do}

def tinh_cau_82(bien_do, vmax, toc_do):
    return bien_do*math.sqrt(1-(toc_do/vmax)**2)
