import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 12)
    omega = random.randint(1, 12)
    return {'bien_do': bien_do, 'omega': omega}

def tinh_L11C1B3_25_TN(bien_do, omega):
    return bien_do*omega**2
