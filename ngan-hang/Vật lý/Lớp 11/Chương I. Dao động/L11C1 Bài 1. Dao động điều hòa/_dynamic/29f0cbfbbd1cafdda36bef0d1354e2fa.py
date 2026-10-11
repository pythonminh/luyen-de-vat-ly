import math
import random

def sinh_so_lieu():
    ban_kinh = random.randint(2, 15)
    toc_do_goc = random.randint(2, 10)
    return {'ban_kinh': ban_kinh, 'toc_do_goc': toc_do_goc}

def tinh_projection(ban_kinh, toc_do_goc):
    return (ban_kinh,toc_do_goc)
