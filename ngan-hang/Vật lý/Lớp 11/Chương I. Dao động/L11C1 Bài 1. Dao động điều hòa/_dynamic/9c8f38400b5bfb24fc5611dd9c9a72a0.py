import math
import random

def sinh_so_lieu():
    thoi_gian_phut = random.randint(1, 4)
    so_dao_dong = random.choice([15, 20, 30, 40, 60, 120])
    return {'thoi_gian_phut': thoi_gian_phut, 'so_dao_dong': so_dao_dong}

def tinh_period(thoi_gian_phut, so_dao_dong):
    return 60*thoi_gian_phut/so_dao_dong
