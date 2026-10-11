import math
import random

def sinh_so_lieu():
    bien_do = random.randint(5, 15)
    omega = random.randint(1, 10)
    toc_do = bien_do * omega * random.choice([0.2, 0.4, 0.6, 0.8])
    return {'bien_do': bien_do, 'omega': omega, 'toc_do': toc_do}

def tinh_L11C1B3_12_TLN(bien_do, omega, toc_do):
    return math.sqrt(bien_do**2-(toc_do/omega)**2)
