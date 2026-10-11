"""Các hàm bài luyện tập Python. Đổi số không gọi AI."""
from fractions import Fraction
from random import randint

# BEGIN 0ac40af36527781e34771c8a21ec4276
def cau_L11C1B3_31_TN_0ac40af36527(dung_so_goc=False):
    for _ in range(100):
        v0 = Fraction('5') if dung_so_goc else (Fraction('4') + Fraction('1') * randint(0, 8))
        v1 = Fraction('2') if dung_so_goc else (Fraction('1') + Fraction('1') * randint(0, 5))
        v3 = Fraction('5/2') if dung_so_goc else (v0 / Fraction('2'))
        if not (v3 ** Fraction('2') * Fraction('3') <= v0 ** Fraction('2')):
            if dung_so_goc: raise ValueError('Số liệu gốc không thỏa điều kiện.')
            continue
        answer = -v1 ** Fraction('2') * v3
        return {'v0': v0, 'v1': v1, 'v3': v3, 'answer': answer}
    raise ValueError('Không sinh được bộ số hợp lệ.')
# END 0ac40af36527781e34771c8a21ec4276
