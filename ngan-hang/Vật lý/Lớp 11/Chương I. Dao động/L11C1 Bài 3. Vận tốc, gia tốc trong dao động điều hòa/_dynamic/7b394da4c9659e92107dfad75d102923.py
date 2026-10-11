import math
import random

def sinh_so_lieu():
    x1 = 3 * random.randint(1, 4)
    x2 = 4 * x1 / 3
    v1 = 4 * random.randint(1, 5)
    v2 = 3 * v1 / 4
    return {'x1': x1, 'v1': v1, 'x2': x2, 'v2': v2}

def tinh_cau_118(x1, v1, x2, v2):
    return math.sqrt((v1**2*x2**2-v2**2*x1**2)/(v1**2-v2**2))
