"""Pure Python oscillator generators. All answers use exact Fraction arithmetic."""
from fractions import Fraction as F
from random import SystemRandom

RNG = SystemRandom()
SPECS = {
    'acceleration': [('A', 'Biên độ (cm)', 2, 12), ('w', 'Hệ số của π trong ω', 1, 8)],
    'amplitude': [('A', 'Biên độ (cm)', 2, 15)],
    'projection': [('R', 'Bán kính (cm)', 2, 15), ('w', 'Tốc độ góc (rad/s)', 2, 10)],
    'period': [('minutes', 'Thời gian (phút)', 1, 4), ('N', 'Số dao động', 15, 60)],
    'orbit': [('A', 'Biên độ (cm)', 2, 12), ('N', 'Số dao động', 2, 20)],
    'rotation': [('R', 'Khoảng cách tới tâm (cm)', 3, 20), ('w', 'Hệ số của π trong tốc độ góc', 1, 10)],
    'spring': [('N', 'Số dao động', 10, 40), ('tenths', 'Chu kì: số phần mười giây', 4, 12), ('grams', 'Khối lượng (g)', 40, 200)],
    'distance': [('A', 'Biên độ (cm)', 1, 12), ('w', 'Hệ số của π trong ω', 2, 12), ('h', 'Số nửa chu kì', 3, 25)],
}

def exact(value):
    value = F(value)
    d = value.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d != 1:
        return f'{value.numerator}/{value.denominator}'
    sign = '-' if value < 0 else ''
    n = abs(value.numerator)
    whole, rem = divmod(n, value.denominator)
    digits = ''
    while rem:
        digit, rem = divmod(rem * 10, value.denominator)
        digits += str(digit)
    return sign + str(whole) + (',' + digits if digits else '')

def fraction(s):
    return F(str(s).strip().replace(',', '.'))

def validate_bounds(key, bounds=None):
    if key not in SPECS:
        raise ValueError('Mẫu bài chưa được hỗ trợ.')
    bounds = bounds or {}
    if not isinstance(bounds, dict) or set(bounds) - {v[0] for v in SPECS[key]}:
        raise ValueError('Biến cấu hình không hợp lệ.')
    result = {}
    for name, _, lo, hi in SPECS[key]:
        raw = bounds.get(name, {'min': lo, 'max': hi})
        if not isinstance(raw, dict):
            raise ValueError('Khoảng số không hợp lệ.')
        a, b = raw.get('min'), raw.get('max')
        if type(a) is not int or type(b) is not int or not 1 <= a <= b <= 1000:
            raise ValueError('Mỗi khoảng phải là số nguyên từ 1 đến 1000, nhỏ nhất ≤ lớn nhất.')
        result[name] = (a, b)
    return result

def generate(key, bounds=None, previous=None):
    ranges = validate_bounds(key, bounds)
    def one():
        v = {name: RNG.randint(*r) for name, r in ranges.items()}
        if key == 'acceleration': p = [v['A'], v['w'], RNG.choice([3,4,6])]
        elif key == 'amplitude': p = [2*v['A']]
        elif key == 'projection': p = [v['R'], v['w']]
        elif key == 'period': p = [v['minutes'], v['N']]
        elif key == 'orbit': p = [v['N'], 4*v['A']*v['N']]
        elif key == 'rotation': p = [v['R'], v['w']]
        elif key == 'spring': p = [v['N'], F(v['N']*v['tenths'], 10), F(v['grams'], 1000)]
        else: p = [v['A'], v['w'], RNG.choice([3,4,6]), F(v['h'],v['w'])]
        return [str(F(x)) for x in p]
    for _ in range(20):
        p = one()
        if previous is None or [fraction(x) for x in p] != [fraction(x) for x in previous]:
            return p
    # A fixed range intentionally produces a fixed exercise.
    return p

def solve(key, params):
    p = list(map(fraction, params))
    if any(x <= 0 for x in p):
        raise ValueError('Số liệu phải dương.')
    f = exact
    unit = 'cm'
    A = None
    candidates = None
    if key == 'acceleration':
        A = p[0]; answer = A*p[1]*p[1]; unit = 'π² cm/s²'
        stem = f'Vật dao động x = {f(A)} cos({f(p[1])}πt + π/{f(p[2])}) cm. Tìm độ lớn gia tốc cực đại.'
        formula = 'a = −ω²x; a_max = ω²A.'
        steps = f'A = {f(A)} cm; ω = {f(p[1])}π rad/s. a_max = ({f(p[1])}π)² × {f(A)} = {f(answer)}π² cm/s².'
    elif key == 'amplitude':
        answer = p[0]/2
        stem = f'Một vật dao động điều hòa trên quỹ đạo dài {f(p[0])} cm. Biên độ của vật là bao nhiêu?'
        formula = 'L = 2A; A = L/2.'
        steps = f'A = {f(p[0])}/2 = {f(answer)} cm.'
    elif key == 'projection':
        A = p[0]; answer = (p[0],p[1]); unit = ''
        stem = f'Chất điểm chuyển động tròn đều với R = {f(p[0])} cm và tốc độ góc {f(p[1])} rad/s. Biên độ và tần số góc của hình chiếu lên đường kính lần lượt là?'
        formula = 'x = R cos(ωt + φ); A = R; ω bằng tốc độ góc quay.'
        steps = f'A = {f(p[0])} cm; ω = {f(p[1])} rad/s.'
        candidates = [(p[0],p[1]),(2*p[0],p[1]),(p[0],2*p[1]),(p[0]/2,p[1])]
    elif key == 'period':
        answer = 60*p[0]/p[1]; unit = 's'
        stem = f'Trong {f(p[0])} phút, vật thực hiện {f(p[1])} dao động toàn phần. Chu kì là bao nhiêu?'
        formula = 'T = Δt/N; f = N/Δt. Đổi phút sang giây.'
        steps = f'Δt = {f(60*p[0])} s. T = {f(60*p[0])}/{f(p[1])} = {f(answer)} s.'
    elif key == 'orbit':
        answer = p[1]/(2*p[0])
        stem = f'Vật thực hiện {f(p[0])} dao động toàn phần và đi được {f(p[1])} cm. Chiều dài quỹ đạo là bao nhiêu?'
        formula = 'S = 4AN; L = 2A = S/(2N).'
        steps = f'L = {f(p[1])}/(2 × {f(p[0])}) = {f(answer)} cm.'
    elif key == 'rotation':
        A = p[0]; answer = (2/p[1],p[1]/2); unit = ''
        stem = f'Thanh nhỏ cách tâm bàn xoay {f(p[0])} cm. Bàn quay đều với tốc độ góc {f(p[1])}π rad/s. Chu kì và tần số của bóng lần lượt là?'
        formula = 'T = 2π/ω; f = 1/T; A = R.'
        steps = f'T = 2/{f(p[1])} = {f(answer[0])} s; f = {f(answer[1])} Hz.'
        candidates = [answer,(2*answer[0],answer[1]/2),(answer[0],2*answer[1]),(answer[0]/2,2*answer[1])]
    elif key == 'spring':
        T = p[1]/p[0]; answer = 40*p[2]/(T*T); unit = 'N/m'
        stem = f'Con lắc lò xo thực hiện {f(p[0])} dao động trong {f(p[1])} s. Khối lượng m = {f(p[2])} kg. Tính k (N/m), lấy π² = 10.'
        formula = 'T = Δt/N; k = 4π²m/T².'
        steps = f'T = {f(p[1])}/{f(p[0])} = {f(T)} s. k = 40 × {f(p[2])}/({f(T)})² = {f(answer)} N/m.'
    elif key == 'distance':
        h = p[1]*p[3]
        if h.denominator != 1:
            raise ValueError('Mẫu này chỉ dùng số nguyên nửa chu kì.')
        A = p[0]; answer = 2*A*h
        stem = f'Vật dao động x = {f(A)} cos({f(p[1])}πt + π/{f(p[2])}) cm. Tính quãng đường trong {f(p[3])} s kể từ t = 0.'
        formula = 'T = 2π/ω. Trong mỗi T/2, vật đi 2A với mọi pha ban đầu.'
        steps = f'T = {f(2/p[1])} s; Δt/(T/2) = {f(h)}. S = {f(h)} × 2 × {f(A)} = {f(answer)} cm.'
    else:
        raise ValueError('Mẫu chưa được hỗ trợ.')
    candidates = candidates or [answer,2*answer,answer/2,3*answer]
    def choice(value):
        if isinstance(value, tuple):
            return f'{f(value[0])} cm; {f(value[1])} rad/s' if key == 'projection' else f'{f(value[0])} s; {f(value[1])} Hz'
        return f(value)+' '+unit
    options = [{'text': choice(v), 'correct': v == answer} for v in candidates]
    RNG.shuffle(options)
    return {'text': stem, 'formula': formula, 'solution': steps, 'answer': ';'.join(map(f,answer)) if isinstance(answer,tuple) else f(answer), 'options': options, 'figure': {'amplitude': f(A) if A is not None else None}, 'params': list(map(f,p)), 'html': False}
