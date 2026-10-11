import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 20)
    he_so_omega = random.randint(1, 8)
    return {'bien_do': bien_do, 'he_so_omega': he_so_omega}

def tinh_L11C1B3_08_TLN(bien_do, he_so_omega):
    return bien_do*he_so_omega**2*10
