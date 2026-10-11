import math
import random

def sinh_so_lieu():
    bien_do = random.randint(5, 15)
    amax = random.randint(2, 12)
    he_so_gia_toc = amax * random.choice([0.2, 0.4, 0.6, 0.8])
    return {'bien_do': bien_do, 'amax': amax, 'he_so_gia_toc': he_so_gia_toc}

def tinh_cau_83(bien_do, amax, he_so_gia_toc):
    return bien_do*he_so_gia_toc/amax
