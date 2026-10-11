import math
import random

def sinh_so_lieu():
    li_do = random.choice([1.5, 2.5, 3, 4.5, 6])
    omega = random.randint(1, 10)
    return {'li_do': li_do, 'omega': omega}

def tinh_L11C1B3_34_TLN(li_do, omega):
    return omega**2*li_do
