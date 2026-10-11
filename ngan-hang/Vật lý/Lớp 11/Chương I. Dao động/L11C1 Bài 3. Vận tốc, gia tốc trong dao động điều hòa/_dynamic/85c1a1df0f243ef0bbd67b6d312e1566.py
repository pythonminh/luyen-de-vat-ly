import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 15)
    chu_ki = random.choice([0.5, 1, 2, 4])
    thoi_gian = chu_ki * random.randint(1, 8)
    return {'bien_do': bien_do, 'chu_ki': chu_ki, 'thoi_gian': thoi_gian}

def tinh_cau_120(bien_do, chu_ki, thoi_gian):
    return 4*bien_do*thoi_gian/chu_ki
