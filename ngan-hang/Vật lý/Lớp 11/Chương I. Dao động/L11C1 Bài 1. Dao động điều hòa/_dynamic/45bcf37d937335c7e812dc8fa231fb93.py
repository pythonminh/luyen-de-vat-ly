import math
import random

def sinh_so_lieu():
    so_dao_dong = random.randint(2, 20)
    quang_duong = 4 * random.randint(2, 12) * so_dao_dong
    return {'so_dao_dong': so_dao_dong, 'quang_duong': quang_duong}

def tinh_orbit(so_dao_dong, quang_duong):
    return quang_duong/(2*so_dao_dong)
