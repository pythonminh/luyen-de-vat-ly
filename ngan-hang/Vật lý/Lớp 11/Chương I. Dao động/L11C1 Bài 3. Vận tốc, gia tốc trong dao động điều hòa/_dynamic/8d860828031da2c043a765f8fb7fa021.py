import math
import random

def sinh_so_lieu():
    he_so_bien_do = random.randint(1, 10)
    he_so_omega = random.randint(1, 10)
    thoi_gian = random.choice([0.25, 0.5, 0.75, 1, 2])
    return {'he_so_bien_do': he_so_bien_do, 'he_so_omega': he_so_omega, 'thoi_gian': thoi_gian}

def tinh_L11C1B3_43_TN(he_so_bien_do, he_so_omega, thoi_gian):
    return he_so_bien_do*math.sqrt(3)*math.cos(he_so_omega*math.pi*thoi_gian+math.pi/3)
