import math
import random

def sinh_so_lieu():
    bien_do = random.choice([2.5, 3, 4, 5, 6, 8])
    he_so_omega = random.randint(2, 12)
    thoi_gian = random.randint(3, 25) / he_so_omega
    return {'bien_do': bien_do, 'he_so_omega': he_so_omega, 'thoi_gian': thoi_gian}

def tinh_distance(bien_do, he_so_omega, thoi_gian):
    return 2*bien_do*he_so_omega*thoi_gian
