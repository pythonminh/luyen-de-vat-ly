"""Hàm tính cho các câu trong bài. App truyền số liệu mới vào hàm."""

# BEGIN 0ac40af36527781e34771c8a21ec4276
import math
import random

# Nút Đổi đề gọi hàm này; không gọi AI.
def sinh_so_lieu():
    bien_do = random.choice([2, 3, 4, 5, 6, 8, 10])
    he_so_omega = random.randint(1, 5)
    return {"bien_do": bien_do, "he_so_omega": he_so_omega}

# Gia tốc tại x = A√3/2, với ω = he_so_omega·π
def tinh_gia_toc(bien_do, he_so_omega):
    omega = he_so_omega * math.pi
    li_do = bien_do * math.sqrt(3) / 2
    return -(omega**2) * li_do
# END 0ac40af36527781e34771c8a21ec4276

# BEGIN cf21b100f629593a8e5aac1120c8fc92
import math
import random

def sinh_so_lieu():
    bien_do = random.randint(2, 12)
    he_so_omega = random.randint(1, 8)
    return {'bien_do': bien_do, 'he_so_omega': he_so_omega}

def tinh_acceleration(bien_do, he_so_omega):
    return bien_do*(he_so_omega*math.pi)**2
# END cf21b100f629593a8e5aac1120c8fc92
