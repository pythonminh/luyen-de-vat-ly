import math
import random

def sinh_so_lieu():
    mau_chu_ki = random.randint(1, 8)
    bien_do = random.randint(5, 15)
    li_do = bien_do * random.choice([0.2, 0.4, 0.6, 0.8])
    return {'mau_chu_ki': mau_chu_ki, 'bien_do': bien_do, 'li_do': li_do}

def tinh_L11C1B3_37_TN(mau_chu_ki, bien_do, li_do):
    return 2*mau_chu_ki*math.sqrt(bien_do**2-li_do**2)
