import math
import random

def sinh_so_lieu():
    bien_do = random.randint(5, 15)
    tan_so = random.randint(1, 8)
    li_do = bien_do * random.choice([0.2, 0.4, 0.6, 0.8])
    return {'bien_do': bien_do, 'tan_so': tan_so, 'li_do': li_do}

def tinh_L11C1B3_51_TN(bien_do, tan_so, li_do):
    return 2*math.pi*tan_so*math.sqrt(bien_do**2-li_do**2)
