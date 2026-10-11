import math
import random

def sinh_so_lieu():
    vmax = random.randint(2, 8) * 10
    toc_do = vmax / 2
    he_so_gia_toc = random.randint(1, 8) * 10
    return {'vmax': vmax, 'toc_do': toc_do, 'he_so_gia_toc': he_so_gia_toc}

def tinh_L11C1B3_86_TN(vmax, toc_do, he_so_gia_toc):
    return vmax*math.sqrt(vmax**2-toc_do**2)/(he_so_gia_toc*math.sqrt(3))
