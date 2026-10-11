import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 12)
    he_so_omega = random.randint(1, 10)
    li_do = bien_do / 2
    return {'bien_do': bien_do, 'he_so_omega': he_so_omega, 'li_do': li_do}

def tinh_cau_92(bien_do, he_so_omega, li_do):
    return li_do*he_so_omega*math.pi/math.asin(li_do/bien_do)/100
