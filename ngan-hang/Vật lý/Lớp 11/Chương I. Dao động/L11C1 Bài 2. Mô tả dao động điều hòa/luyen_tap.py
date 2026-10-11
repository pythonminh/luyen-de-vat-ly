"""Chương trình riêng từng câu: sinh số và tính đáp án bằng Python."""

# BEGIN b241e7bb10161c42beef2eea8d44fa1a
import math
import random

def sinh_so_lieu():
    thoi_gian_phut = random.randint(1, 4)
    so_dao_dong = random.choice([15, 20, 30, 40, 60, 120])
    return {'thoi_gian_phut': thoi_gian_phut, 'so_dao_dong': so_dao_dong}

def tinh_period(thoi_gian_phut, so_dao_dong):
    return 60*thoi_gian_phut/so_dao_dong
# END b241e7bb10161c42beef2eea8d44fa1a

# BEGIN fd8385778851898e9babae27199b0053
import math
import random

def sinh_so_lieu():
    chieu_dai = 2 * random.randint(2, 15)
    return {'chieu_dai': chieu_dai}

def tinh_amplitude(chieu_dai):
    return chieu_dai/2
# END fd8385778851898e9babae27199b0053
