"""Conservative triangle solvers and saved question programs for numeric race papers."""
import ast
import copy
import math
import random
import re
from decimal import Decimal, ROUND_HALF_UP, localcontext

import sympy as sp

RNG = random.SystemRandom()


def triangle_spec(q):
    if q.get('kind') not in ('TLN', 'TL'):
        return None
    text = str(q.get('text') or '')
    if any(x in text.lower() for x in ('tứ giác', 'đường cao', 'phân giác', 'trung tuyến', 'nội tiếp', 'chứng minh', 'includegraphics', 'tikzpicture', 'làm tròn')):
        return None
    if 'tam giác' not in text.lower() and 'định lý sin' not in text.lower():
        return None
    plain = re.sub(r'\\(?:widehat|hat)\s*(?:\{([ABC])\}|([ABC]))', lambda m: m[1] or m[2], text)
    plain = re.sub(r'\\[(),;!]', ' ', plain).replace('\\circ', '').replace('$', '').replace('^', '').replace('{', '').replace('}', '')
    matches = re.findall(r'(?<![A-Za-z])(AB|AC|BC|a|b|c|A|B|C)\s*=\s*(\d+(?:[.,]\d+)?)', plain)
    data = {k: str(sp.Rational(v.replace(',', '.'))) for k, v in matches}
    if len(matches) != len(data) or any(sp.Rational(v) <= 0 for v in data.values()):
        return None
    keys = set(data)
    kind = None
    if keys == {'AB','AC','A'} and ('BC' in plain or 'ngoại tiếp' in plain):
        kind = 'sas_radius' if 'ngoại tiếp' in plain else 'sas'
    elif keys == {'AB','AC','BC'} and re.search(r'Tính\s+(?:góc\s+)?A', plain, re.I):
        kind = 'sss_area' if 'diện tích' in plain else 'sss'
    elif keys == {'BC','A','B'} and ('CA' in plain or 'AC' in plain):
        kind = 'sine_side'
    elif keys == {'c','A','B'} and 'giải tam giác' in plain.lower():
        kind = 'solve_triangle'
    elif keys == {'a','b','A'} and 'bao nhiêu tam giác' in plain.lower():
        kind = 'ambiguous'
    if not kind:
        return None
    try:
        solve_triangle(kind, {k: sp.Rational(v) for k, v in data.items()})
    except (ValueError, TypeError):
        return None
    return {'engine':'triangle', 'type':kind, 'data':data}


def spec(q):
    from race_linear_ds import spec as linear_spec
    value = linear_spec(q)
    if value:
        return value
    value = triangle_spec(q)
    if value:
        return value
    from race_set_variants import spec as set_spec
    value = set_spec(q)
    if value:
        return value
    try:
        from variable_templates import load_config
        config = load_config(q)
        if config:
            return {'engine':'saved', 'config':config}
    except (ValueError, TypeError, ImportError):
        pass
    return None


def degree(x):
    return sp.Rational(x) * sp.pi / 180


def fmt(x):
    return sp.latex(sp.simplify(x))


def solve_triangle(kind, p):
    """Return a fresh stem, exact solution and ordered exact answers."""
    if kind.startswith('sas'):
        c,b,A = p['AB'],p['AC'],p['A']
        if not 0 < A < 180:
            raise ValueError('Góc không hợp lệ.')
        a = sp.sqrt(c*c+b*b-2*b*c*sp.cos(degree(A)))
        stem = f'Cho tam giác $ABC$ có $AB={fmt(c)}$, $AC={fmt(b)}$, $\\widehat{{A}}={fmt(A)}^\\circ$. '
        solution = f'Định lí cosin: $BC^2={fmt(c)}^2+{fmt(b)}^2-2\\cdot {fmt(c)}\\cdot {fmt(b)}\\cos {fmt(A)}^\\circ={fmt(sp.simplify(a*a))}$. Vậy $BC={fmt(a)}$.'
        if kind == 'sas_radius':
            R = sp.simplify(a/(2*sp.sin(degree(A))))
            stem += 'Tính $BC$ và bán kính đường tròn ngoại tiếp $R$.'
            solution += f' Định lí sin mở rộng: $R=BC/(2\\sin A)={fmt(R)}$.'
            return stem, solution, [a,R], 'BC; R'
        return stem+'Tính độ dài cạnh $BC$.', solution, [a], 'BC'
    if kind.startswith('sss'):
        c,b,a = p['AB'],p['AC'],p['BC']
        if min(a,b,c) <= 0 or not abs(b-c) < a < b+c:
            raise ValueError('Không thỏa bất đẳng thức tam giác.')
        cosA = sp.cancel((b*b+c*c-a*a)/(2*b*c))
        A = 180*sp.acos(cosA)/sp.pi
        stem = f'Cho tam giác $ABC$ có $AB={fmt(c)}$, $AC={fmt(b)}$, $BC={fmt(a)}$. Tính góc $\\widehat{{A}}$'
        solution = f'$\\cos A=\\dfrac{{{fmt(b)}^2+{fmt(c)}^2-{fmt(a)}^2}}{{2\\cdot {fmt(b)}\\cdot {fmt(c)}}}={fmt(cosA)}$. Suy ra $A={fmt(A)}^\\circ$.'
        if kind == 'sss_area':
            S = sp.sqrt((a+b+c)*(-a+b+c)*(a-b+c)*(a+b-c))/4
            solution += f' Diện tích: $S=\\dfrac12 AB\\cdot AC\\sin A={fmt(S)}$.'
            return stem+' và diện tích tam giác.', solution, [A,S], 'A (độ); S'
        return stem+'.', solution, [A], 'A (độ)'
    if kind in ('sine_side','solve_triangle'):
        A,B = p['A'],p['B']; C = 180-A-B
        if min(A,B,C) <= 0:
            raise ValueError('Tổng góc không hợp lệ.')
        if kind == 'sine_side':
            a=p['BC'];b=sp.simplify(a*sp.sin(degree(B))/sp.sin(degree(A)))
            stem = f'Cho tam giác $ABC$ có $BC={fmt(a)}$, $\\widehat{{A}}={fmt(A)}^\\circ$, $\\widehat{{B}}={fmt(B)}^\\circ$. Tính cạnh $CA$.'
            solution=f'Định lí sin: $CA=BC\\cdot\\sin B/\\sin A={fmt(a)}\\cdot\\sin {fmt(B)}^\\circ/\\sin {fmt(A)}^\\circ={fmt(b)}$.'
            return stem,solution,[b],'CA'
        c=p['c'];a=sp.simplify(c*sp.sin(degree(A))/sp.sin(degree(C)));b=sp.simplify(c*sp.sin(degree(B))/sp.sin(degree(C)))
        stem=f'Giải tam giác $ABC$, biết $c={fmt(c)}$, $\\widehat{{A}}={fmt(A)}^\\circ$, $\\widehat{{B}}={fmt(B)}^\\circ$.'
        solution=f'$C=180^\\circ-{fmt(A)}^\\circ-{fmt(B)}^\\circ={fmt(C)}^\\circ$. Định lí sin: $a=c\\sin A/\\sin C={fmt(a)}$; $b=c\\sin B/\\sin C={fmt(b)}$.'
        return stem,solution,[C,a,b],'C (độ); a; b'
    if kind == 'ambiguous':
        a,b,A=p['a'],p['b'],p['A'];ratio=sp.simplify(b*sp.sin(degree(A))/a)
        if not 0 < ratio < 1:
            raise ValueError('Không còn hai nghiệm phân biệt.')
        B1=180*sp.asin(ratio)/sp.pi;B2=180-B1;C1=180-A-B1;C2=180-A-B2
        if min(float(C1),float(C2)) <= 0:
            raise ValueError('Không có hai tam giác.')
        stem=f'Cho tam giác có $a={fmt(a)}$, $b={fmt(b)}$, $\\widehat{{A}}={fmt(A)}^\\circ$. Hỏi có bao nhiêu tam giác thỏa mãn? Tính các góc có thể có.'
        solution=f'$\\sin B=b\\sin A/a={fmt(ratio)}$. Có $B_1={fmt(B1)}^\\circ$, $B_2={fmt(B2)}^\\circ$. Hai giá trị đều thỏa $A+B<180^\\circ$ nên có 2 tam giác. $C_1={fmt(C1)}^\\circ$; $C_2={fmt(C2)}^\\circ$.'
        return stem,solution,[sp.Integer(2),B1,C1,B2,C2],'số tam giác; B1; C1; B2; C2 (góc theo độ)'
    raise ValueError('Chưa có bộ đổi số cho dạng này.')


def random_data(s):
    p={k:sp.Rational(v) for k,v in s['data'].items()};kind=s['type']
    if kind.startswith('sas'):
        p.update(AB=sp.Integer(RNG.randint(4,35)),AC=sp.Integer(RNG.randint(4,35)),A=sp.Integer(RNG.choice([30,45,60] if p['A']<90 else [105,120,135,150] if p['A']>90 else [90])))
    elif kind.startswith('sss'):
        b,c,a=p['AC'],p['AB'],p['BC']
        if sorted([a*a,b*b,c*c])[2] == sum(sorted([a*a,b*b,c*c])[:2]):
            m=RNG.randint(2,8);n=RNG.randint(1,m-1);k=RNG.randint(1,4)
            sides=[sp.Integer(2*m*n*k),sp.Integer((m*m-n*n)*k),sp.Integer((m*m+n*n)*k)]
            largest=max(range(3),key=lambda i:[a,b,c][i]);others=[i for i in range(3) if i!=largest]
            values=[None]*3;values[largest]=sides[2];values[others[0]],values[others[1]]=sides[:2]
            a,b,c=values
        else:
            for _ in range(100):
                b,c=sp.Integer(RNG.randint(4,25)),sp.Integer(RNG.randint(4,25));choices=[v for v in range(int(abs(b-c))+1,int(b+c)) if (v*v>b*b+c*c)==(p['BC']**2>p['AC']**2+p['AB']**2)]
                if choices:
                    a=sp.Integer(RNG.choice(choices));break
            else:raise ValueError('Chưa sinh được tam giác phù hợp.')
        p.update(AB=c,AC=b,BC=a)
    elif kind in ('sine_side','solve_triangle'):
        angles=[30,45,60,75] if kind=='sine_side' else [30,40,45,50,60,70,75]
        A=RNG.choice(angles);B=RNG.choice([v for v in angles if A+v<160]);p.update(A=sp.Integer(A),B=sp.Integer(B))
        p['BC' if kind=='sine_side' else 'c']=sp.Integer(RNG.randint(5,50))
    elif kind=='ambiguous':
        a=RNG.randint(6,35);p.update(a=sp.Integer(a),b=sp.Integer(RNG.randint(a+1,2*a-1)),A=sp.Integer(30))
    return p


DECIMAL_HINT = 'Kết quả không nguyên làm tròn đến 2 chữ số sau dấu phẩy. Dùng dấu phẩy (,) làm dấu thập phân, ví dụ 8,19; dùng dấu chấm phẩy (;) giữa các kết quả. Số nguyên giữ nguyên.'


def decimal_value(value):
    with localcontext() as ctx:
        ctx.prec = 60
        exact = parse_expression(str(value), False)
        if exact.is_Integer:
            return str(exact)
        rounded = Decimal(str(sp.N(exact, 55))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return format(abs(rounded) if rounded == 0 else rounded, '.2f')


def decimalize(q):
    if q.get('kind') == 'TN':
        return q
    values = q.get('_race_answer_components')
    if not values and '_race_saved_answer' in q:
        values = [q['_race_saved_answer']]
    if not values:
        return q
    try:
        rounded = [decimal_value(v) for v in values]
    except (ValueError, TypeError, SyntaxError):
        return q
    q['_race_rounded_components'] = rounded
    q['_race_decimal_places'] = 2
    q['_race_answer_display'] = '$' + r';\quad '.join(v.replace('.', '{,}') for v in rounded) + '$'
    q['_race_answer_hint'] = DECIMAL_HINT
    q['solution'] = str(q.get('solution') or '') + '\nKết quả nhập (đã làm tròn): ' + q['_race_answer_display'] + '.'
    return q


def generate(q, original=False):
    s=q.get('_race_variant_spec') or spec(q)
    if not s:
        raise ValueError('Câu này chưa có hàm đổi số đã kiểm tra.')
    out=copy.deepcopy(q)
    if s['engine']=='linear_ds':
        from race_linear_ds import generate as generate_linear
        return generate_linear(q, s, original)
    if s['engine']=='sets':
        from race_set_variants import generate as generate_sets
        return decimalize(generate_sets(q, s, original))
    if s['engine']=='saved':
        from variable_templates import generate_custom
        ex=generate_custom(q,s['config'],original=original)
        out.update({k:ex[k] for k in ('text','solution','answer','kind','options') if k in ex})
        out['_race_saved_answer']=ex['answer']
        return decimalize(out)
    p={k:sp.Rational(v) for k,v in s['data'].items()} if original else random_data(s)
    if not original and all(p[k]==sp.Rational(v) for k,v in s['data'].items()):
        return generate(q,False)
    stem,solution,components,order=solve_triangle(s['type'],p)
    out['text']=(q['text'] if original else stem)+f'\nNhập theo thứ tự: {order}. Dùng dấu chấm phẩy (;) giữa các kết quả. Các góc tính theo độ.'
    out['solution']=solution+'\nĐáp án theo thứ tự: $'+r';\quad '.join(fmt(v) for v in components)+'$.'
    out['_race_answer_components']=[str(sp.simplify(v)) for v in components]
    out['_race_order']=order
    out['_race_variant_values']={k:str(v) for k,v in p.items()}
    out['_race_variant_spec']=s
    return decimalize(out)


def parse_expression(text, degrees=True):
    text=str(text).strip().replace('−','-').replace('π','pi').replace('^','**').replace(',', '.')
    text=re.sub(r'√\s*(\d+)',r'sqrt(\1)',text)
    if not 0<len(text)<=300:
        raise ValueError('Biểu thức quá dài.')
    for exponent in re.findall(r'[eE]([+-]?\d+)', text):
        if len(exponent.lstrip('+-')) > 3 or abs(int(exponent)) > 100:
            raise ValueError('Số mũ vượt giới hạn.')
    tree=ast.parse(text,mode='eval')
    if len(list(ast.walk(tree)))>60:
        raise ValueError('Biểu thức quá phức tạp.')
    funcs={'sqrt':sp.sqrt,'sin':sp.sin,'cos':sp.cos,'tan':sp.tan,'asin':sp.asin,'acos':sp.acos}
    def value(n):
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):
            x=sp.Rational(ast.get_source_segment(text,n))
            if abs(x)>10**8:raise ValueError('Số vượt giới hạn.')
            return x
        if isinstance(n,ast.Name) and n.id=='pi':return sp.pi
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            v=value(n.operand);return -v if isinstance(n.op,ast.USub) else v
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
            a,b=value(n.left),value(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b
            if b.is_Integer is not True or abs(b)>6:raise ValueError('Số mũ vượt giới hạn.')
            if isinstance(a, sp.Rational) and max(int(a.p).bit_length(), int(a.q).bit_length()) * max(1,abs(int(b))) > 4096:
                raise ValueError('Biểu thức vượt giới hạn.')
            return a**b
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in funcs and len(n.args)==1 and not n.keywords:
            x=value(n.args[0]);name=n.func.id
            if degrees and name in ('sin','cos','tan'):x=x*sp.pi/180
            y=funcs[name](x)
            return y*180/sp.pi if degrees and name in ('asin','acos') else y
        raise ValueError('Chỉ dùng số, phép tính, sqrt và hàm lượng giác.')
    result=value(tree.body)
    if result.is_real is not True or result.is_finite is not True:
        raise ValueError('Kết quả không thực hoặc không hữu hạn.')
    return result


def matches(q, answer):
    rounded = q.get('_race_rounded_components')
    if rounded and isinstance(answer, str):
        parts = answer.strip().split(';')
        try:
            if len(parts) == len(rounded) and all(abs(float(sp.N(parse_expression(a)-sp.Rational(b), 20))) < 1e-9 for a,b in zip(parts, rounded)):
                return True
        except (ValueError, TypeError, SyntaxError, ZeroDivisionError, OverflowError):
            pass
    if q.get('_race_set_answer'):
        from race_set_variants import matches as set_matches
        return set_matches(q, answer)
    if '_race_saved_answer' in q:
        from python_questions import same_answer
        try:return bool(same_answer(answer,q['_race_saved_answer']))
        except Exception:return False
    if not isinstance(answer,str):return False
    expected=q.get('_race_answer_components') or []
    parts=answer.strip().split(';')
    if len(parts)!=len(expected):return False
    try:
        actual=[parse_expression(v) for v in parts];target=[parse_expression(v,False) for v in expected]
        def close(xs,ys):
            for a,b in zip(xs,ys):
                if a==b:continue
                delta=sp.N(a-b,18)
                if abs(float(delta))>1e-9:return False
            return True
        if close(actual,target):return True
        if q.get('_race_variant_spec',{}).get('type')=='ambiguous':
            return close(actual,[target[0],target[3],target[4],target[1],target[2]])
    except (ValueError,TypeError,SyntaxError,ZeroDivisionError,OverflowError):
        return False
    return False
