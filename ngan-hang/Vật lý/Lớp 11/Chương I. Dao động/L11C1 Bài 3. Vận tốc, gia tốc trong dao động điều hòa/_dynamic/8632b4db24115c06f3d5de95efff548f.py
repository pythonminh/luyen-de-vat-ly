import math
import random

def sinh_so_lieu():
    chieu_dai = random.randint(5, 25)
    vong_moi_phut = random.randint(5, 30) * 60
    return {'chieu_dai': chieu_dai, 'vong_moi_phut': vong_moi_phut}

def tinh_cau_106(chieu_dai, vong_moi_phut):
    return 3.14*chieu_dai*vong_moi_phut/6000
