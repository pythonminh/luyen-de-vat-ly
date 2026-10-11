"""Hàm tính cho các câu trong bài. App truyền số liệu mới vào hàm."""

# BEGIN 0ac40af36527781e34771c8a21ec4276
import math

# Gia tốc tại x = A√3/2, với ω = he_so_omega·π
def tinh_gia_toc(bien_do, he_so_omega):
    omega = he_so_omega * math.pi
    li_do = bien_do * math.sqrt(3) / 2
    return -(omega**2) * li_do
# END 0ac40af36527781e34771c8a21ec4276
