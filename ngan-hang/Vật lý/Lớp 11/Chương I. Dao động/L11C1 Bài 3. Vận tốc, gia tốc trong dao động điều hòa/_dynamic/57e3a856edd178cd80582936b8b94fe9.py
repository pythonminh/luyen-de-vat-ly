import math
import random

def sinh_so_lieu():
    li_do1 = random.randint(2, 10)
    vmax = random.randint(2, 10) * 10
    toc_do1 = vmax * 0.8
    toc_do2 = vmax * 0.6
    return {'li_do1': li_do1, 'toc_do1': toc_do1, 'vmax': vmax, 'toc_do2': toc_do2}

def tinh_cau_87(li_do1, toc_do1, vmax, toc_do2):
    return li_do1*math.sqrt((vmax**2-toc_do2**2)/(vmax**2-toc_do1**2))
