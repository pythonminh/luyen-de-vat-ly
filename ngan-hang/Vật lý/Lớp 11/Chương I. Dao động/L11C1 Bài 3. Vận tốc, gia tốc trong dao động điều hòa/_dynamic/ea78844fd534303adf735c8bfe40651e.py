import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 12)
    mau_thoi_gian = random.choice([4, 8, 12])
    omega = mau_thoi_gian * random.choice([0.5, 1.5, 2.5])
    return {'bien_do': bien_do, 'omega': omega, 'mau_thoi_gian': mau_thoi_gian}

def tinh_L11C1B3_48_TN(bien_do, omega, mau_thoi_gian):
    return -bien_do*omega*math.sin(omega*math.pi/mau_thoi_gian)
