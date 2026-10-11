"""Chương trình riêng từng câu: sinh số và tính đáp án bằng Python."""

# BEGIN f20018e407753307aefd88a3b1d782ab
import math
import random

def sinh_so_lieu():
    so_dao_dong = random.randint(10, 40)
    thoi_gian = so_dao_dong * random.randint(4, 12) / 10
    khoi_luong = random.randint(4, 20) / 100
    return {'so_dao_dong': so_dao_dong, 'thoi_gian': thoi_gian, 'khoi_luong': khoi_luong}

def tinh_spring(so_dao_dong, thoi_gian, khoi_luong):
    return 40*khoi_luong/(thoi_gian/so_dao_dong)**2
# END f20018e407753307aefd88a3b1d782ab

# BEGIN ed62f0a70805f03053413229b96e3352
import math
import random

def sinh_so_lieu():
    chieu_dai = 2 * random.randint(2, 15)
    return {'chieu_dai': chieu_dai}

def tinh_amplitude(chieu_dai):
    return chieu_dai/2
# END ed62f0a70805f03053413229b96e3352

# BEGIN 29f0cbfbbd1cafdda36bef0d1354e2fa
import math
import random

def sinh_so_lieu():
    ban_kinh = random.randint(2, 15)
    toc_do_goc = random.randint(2, 10)
    return {'ban_kinh': ban_kinh, 'toc_do_goc': toc_do_goc}

def tinh_projection(ban_kinh, toc_do_goc):
    return (ban_kinh,toc_do_goc)
# END 29f0cbfbbd1cafdda36bef0d1354e2fa

# BEGIN 9c8f38400b5bfb24fc5611dd9c9a72a0
import math
import random

def sinh_so_lieu():
    thoi_gian_phut = random.randint(1, 4)
    so_dao_dong = random.choice([15, 20, 30, 40, 60, 120])
    return {'thoi_gian_phut': thoi_gian_phut, 'so_dao_dong': so_dao_dong}

def tinh_period(thoi_gian_phut, so_dao_dong):
    return 60*thoi_gian_phut/so_dao_dong
# END 9c8f38400b5bfb24fc5611dd9c9a72a0

# BEGIN 9d0dfa4a4a1ce56e4699ea009daf9798
import math
import random

def sinh_so_lieu():
    ban_kinh = random.randint(3, 20)
    he_so_omega = random.randint(1, 10)
    return {'ban_kinh': ban_kinh, 'he_so_omega': he_so_omega}

def tinh_rotation(ban_kinh, he_so_omega):
    return (2/he_so_omega,he_so_omega/2)
# END 9d0dfa4a4a1ce56e4699ea009daf9798

# BEGIN 45bcf37d937335c7e812dc8fa231fb93
import math
import random

def sinh_so_lieu():
    so_dao_dong = random.randint(2, 20)
    quang_duong = 4 * random.randint(2, 12) * so_dao_dong
    return {'so_dao_dong': so_dao_dong, 'quang_duong': quang_duong}

def tinh_orbit(so_dao_dong, quang_duong):
    return quang_duong/(2*so_dao_dong)
# END 45bcf37d937335c7e812dc8fa231fb93
