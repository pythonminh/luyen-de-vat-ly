import math
import random

def sinh_so_lieu():
    bien_do = random.randint(1, 4)
    chu_ki = 3.14 * random.choice([0.5, 1, 2, 4])
    return {'chu_ki': chu_ki, 'bien_do': bien_do}

def tinh_cau_114(chu_ki, bien_do):
    return 2*3.14*bien_do/chu_ki
