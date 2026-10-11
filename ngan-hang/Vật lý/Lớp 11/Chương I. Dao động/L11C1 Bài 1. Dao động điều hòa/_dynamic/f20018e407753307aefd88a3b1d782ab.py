import math
import random

def sinh_so_lieu():
    so_dao_dong = random.randint(10, 40)
    thoi_gian = so_dao_dong * random.randint(4, 12) / 10
    khoi_luong = random.randint(4, 20) / 100
    return {'so_dao_dong': so_dao_dong, 'thoi_gian': thoi_gian, 'khoi_luong': khoi_luong}

def tinh_spring(so_dao_dong, thoi_gian, khoi_luong):
    return 40*khoi_luong/(thoi_gian/so_dao_dong)**2
