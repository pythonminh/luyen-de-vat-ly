import math
import random

def sinh_so_lieu():
    omega = random.randint(1, 10)
    li_do = random.randint(1, 8)
    return {'omega': omega, 'li_do': li_do}

def tinh_L11C1B3_05_TLN(omega, li_do):
    return -omega**2*li_do
