import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 15)
    omega = random.randint(1, 10)
    return {'bien_do': bien_do, 'omega': omega}

def tinh_cau_77(bien_do, omega):
    return bien_do*omega
