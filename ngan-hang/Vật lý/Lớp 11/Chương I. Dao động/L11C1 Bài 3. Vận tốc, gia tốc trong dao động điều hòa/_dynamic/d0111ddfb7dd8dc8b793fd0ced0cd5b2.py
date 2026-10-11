import math
import random

def sinh_so_lieu():
    bien_do = random.randint(5, 20)
    he_so_vmax = random.randint(5, 20)
    toc_do = he_so_vmax
    return {'bien_do': bien_do, 'he_so_vmax': he_so_vmax, 'toc_do': toc_do}

def tinh_cau_81(bien_do, he_so_vmax, toc_do):
    return bien_do*math.sqrt(1-toc_do**2/(2*he_so_vmax**2))
