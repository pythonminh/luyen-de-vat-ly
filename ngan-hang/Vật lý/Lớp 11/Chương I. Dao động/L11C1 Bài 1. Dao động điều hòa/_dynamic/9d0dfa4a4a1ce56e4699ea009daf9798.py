import math
import random

def sinh_so_lieu():
    ban_kinh = random.randint(3, 20)
    he_so_omega = random.randint(1, 10)
    return {'ban_kinh': ban_kinh, 'he_so_omega': he_so_omega}

def tinh_rotation(ban_kinh, he_so_omega):
    return (2/he_so_omega,he_so_omega/2)
