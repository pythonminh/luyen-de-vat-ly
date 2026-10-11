import math
import random

def sinh_so_lieu():
    omega = random.randint(1, 10)
    li_do = random.randint(2, 10)
    toc_do = omega * random.randint(2, 10)
    return {'omega': omega, 'li_do': li_do, 'toc_do': toc_do}

def tinh_cau_85(omega, li_do, toc_do):
    return math.sqrt(li_do**2+(toc_do/omega)**2)
