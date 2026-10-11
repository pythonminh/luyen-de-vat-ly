import math
import random

def sinh_so_lieu():
    chieu_dai = 2 * random.randint(5, 20)
    li_do = chieu_dai/2 * random.choice([0.2, 0.4, 0.6, 0.8])
    he_so_toc_do = random.randint(5, 50)
    return {'chieu_dai': chieu_dai, 'li_do': li_do, 'he_so_toc_do': he_so_toc_do}

def tinh_cau_116(chieu_dai, li_do, he_so_toc_do):
    return math.sqrt((chieu_dai/2)**2-li_do**2)/he_so_toc_do
