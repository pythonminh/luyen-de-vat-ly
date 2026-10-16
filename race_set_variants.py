"""Verified generators for seven parameter/interval questions in the bank.

Match the complete source stem, so editing a question invalidates its solver rather
than silently applying formulas to a different problem.
"""
import copy
import hashlib
import random
import re
from decimal import Decimal, ROUND_HALF_UP, localcontext
import sympy as sp

RNG = random.SystemRandom()
m, a = sp.symbols('m a', real=True)
REGISTRY = {
 'd96b59b8c3279e11ba3eba4a4f02e63467fa573b1ffd04b958daa4a730e1cfd3': ('positive_subset', {'u':1,'v':4,'l':-2,'k':2,'t':2}),
 '5c3d8c654fc2db2ef1d1051dc30604f4fb735a15073d72932ca7d1f0ca248b7d': ('empty_intersection', {'u':3,'v':2,'k':4,'l':-1,'r':2}),
 'b4957c45cc199e0d42c1e78afc8959ede06cdc9eea94995ab520c1ecc881055e': ('closed_subset_count', {'u':1,'v':1,'k':2,'l':0,'r':6}),
 '54c9992435e9e5a06a210a1640aa861832637cb79cd6cf72da5dec49d85989f4': ('singleton_positive', {'h':3,'t':8}),
 'a046740e0a3560f0b074df0c3364f8b4b302e1ee263857dd5cb00c239369f657': ('power_set_count', {'u':4,'v':7,'k':2,'p':-1,'l':3,'q':5}),
 '2f154cccb551ecd5ecb6cc7f164e4573f1efb98a29568a4465a34b3f5183306a': ('negative_overlap', {'k':9,'t':4}),
 'bc76d61b677232e2171b9e4269171866a3618aa45e20f0ffa9087ee8de2e8d98': ('open_subset_count', {'u':1,'v':5,'k':4,'t':1}),
}


def spec(q):
    key=hashlib.sha256(re.sub(r'\s+', '', str(q.get('text') or '')).encode()).hexdigest()
    if key not in REGISTRY or q.get('kind') not in ('TL','TLN'):
        return None
    kind, data=REGISTRY[key]
    return {'engine':'sets', 'type':kind, 'data':data}


def tex(x):
    return sp.latex(sp.sympify(x))


def integer_values(lower, upper, left_open=False, right_open=False):
    lo=int(sp.floor(lower)+1 if left_open else sp.ceiling(lower))
    hi=int(sp.ceiling(upper)-1 if right_open else sp.floor(upper))
    return list(range(lo,hi+1))


def solve(kind, raw):
    p={k:sp.Rational(v) for k,v in raw.items()}
    if kind=='positive_subset':
        u,v,l,k,t=[p[x] for x in ('u','v','l','k','t')]
        lower=max(sp.Integer(1),sp.ceiling(l+u),sp.floor((v-t)/k)+1,sp.floor((l-t)/k)+1)
        vals=integer_values(lower,v+u,right_open=True)
        stem=f'Cho hai tập khác rỗng $A=({tex(m-u)};{tex(v)}]$, $B=({tex(l)};{tex(k*m+t)})$. Tìm tất cả $m$ nguyên dương để $A\\subset B$.'
        solution=f'$A\\ne\\varnothing\\Leftrightarrow m<{tex(v+u)}$; $B\\ne\\varnothing\\Leftrightarrow m>{tex((l-t)/k)}$. Vì đầu phải của $A$ đóng còn đầu phải của $B$ mở, phải có ${tex(v)}<{tex(k*m+t)}$. Đầu trái đều mở nên ${tex(m-u)}\\ge {tex(l)}$. Kết hợp $m\\in\\mathbb{{Z}}$, $m>0$ thu được $m\\in {tex(sp.FiniteSet(*vals))}$.'
        return stem,solution,{'type':'finite','values':[str(x) for x in vals]},'Nhập tất cả giá trị m, cách nhau bởi dấu ; (ví dụ 2;3;4); nếu không có nhập rỗng.'
    if kind=='empty_intersection':
        u,v,k,l,r=[p[x] for x in ('u','v','k','l','r')]
        empty=(k*u+v)/(k-1);low=l+u;high=k*r-v
        inside=sp.Interval(low,high) if low<=high else sp.S.EmptySet
        result=sp.Union(sp.Interval(empty,sp.oo),inside)
        stem=f'Cho $A=\\{{x\\in\\mathbb{{R}}\\mid {tex(m-u)}\\le x<\\dfrac{{{tex(m+v)}}}{{{tex(k)}}}\\}}$, $B=(-\\infty;{tex(l)})\\cup[{tex(r)};+\\infty)$. Tìm $m$ để $A\\cap B=\\varnothing$ (kể cả trường hợp $A$ rỗng).'
        solution=f'Nếu $A$ rỗng thì ${tex(m-u)}\\ge\\dfrac{{{tex(m+v)}}}{{{tex(k)}}}\\Leftrightarrow m\\ge {tex(empty)}$. Nếu $A$ khác rỗng, để không giao $B$ thì $A\\subset[{tex(l)};{tex(r)})$, tức $m\\ge {tex(low)}$ và $m\\le {tex(high)}$. Hợp với trường hợp rỗng cho $m\\in {tex(result)}$.'
        pieces=list(result.args) if isinstance(result,sp.Union) else [result]
        bounds=[]
        for piece in pieces:
            if isinstance(piece,sp.FiniteSet):
                bounds.extend([[str(x),str(x),False,False] for x in piece])
            else:
                bounds.append([str(piece.start),str(piece.end),bool(piece.left_open),bool(piece.right_open)])
        answer={'type':'intervals','values':bounds}
        return stem,solution,answer,'Nhập khoảng/đoạn, dùng dấu ; giữa hai đầu, U để hợp và inf cho vô cực. Đầu mút giữ phân số chính xác để không thay đổi biên của tập hợp. Ví dụ [2;+inf) hoặc [1;3] U [5;+inf).'
    if kind=='closed_subset_count':
        u,v,k,l,r=[p[x] for x in ('u','v','k','l','r')]
        nonempty=(u+v)/(k-1);left=l-u;right=(r+v)/k
        vals=integer_values(max(sp.ceiling(nonempty),sp.floor(left)+1),right,right_open=True)
        stem=f'Cho $A=[{tex(m+u)};{tex(k*m-v)}]$ khác rỗng, $B=({tex(l)};{tex(r)})$. Có bao nhiêu giá trị nguyên của $m$ để $A\\subset B$?'
        solution=f'$A$ khác rỗng khi $m\\ge {tex(nonempty)}$. Hai đầu của $B$ mở, nên ${tex(m+u)}>{tex(l)}$ và ${tex(k*m-v)}<{tex(r)}$, hay $m>{tex(left)}$, $m<{tex(right)}$. Các giá trị nguyên thỏa mãn là ${tex(sp.FiniteSet(*vals))}$. Có ${len(vals)}$ giá trị.'
        return stem,solution,{'type':'scalar','value':str(len(vals))},'Chỉ nhập số giá trị nguyên. Điều kiện A khác rỗng được nêu rõ trong đề.'
    if kind=='singleton_positive':
        h,t=p['h'],p['t'];positive=(t+sp.sqrt(t*t+4*h*h))/2;negative=(t-sp.sqrt(t*t+4*h*h))/2
        stem=f'Cho $A=(0;+\\infty)$ và $B=\\{{x\\in\\mathbb{{R}}\\mid mx^2-{tex(2*h)}x+m-{tex(t)}=0\\}}$. Tìm $m$ để $B$ có đúng hai tập con và $B\\subset A$.'
        solution=f'$B$ có đúng hai tập con nên $|B|=1$. Với $m=0$, nghiệm $x=-{tex(t/(2*h))}<0$ không thuộc $A$. Với $m\\ne0$, cần $\\Delta\'= {tex(h*h)}-m(m-{tex(t)})=0$, suy ra $m={tex(positive)}$ hoặc $m={tex(negative)}$. Nghiệm kép $x={tex(h)}/m$ dương chỉ khi $m>0$. Vậy $m={tex(positive)}$ (khi đó $x={tex(sp.simplify(h/positive))}$).'
        return stem,solution,{'type':'scalar','value':str(sp.simplify(positive))},'Nhập giá trị m chính xác; dùng sqrt(...) nếu cần.'
    if kind=='power_set_count':
        u,v,k,b,l,c=[p[x] for x in ('u','v','k','p','l','q')]
        left=(v-c)/l;right=(u-b)/k;vals=integer_values(left,right,right_open=True)
        stem=f'Cho $A=[{tex(u)};{tex(v)}]$, $B=({tex(k*a+b)};{tex(l*a+c)}]$ khác rỗng. Gọi $S$ là tập các giá trị nguyên của $a$ để $A\\subset B$. Có bao nhiêu tập con của $S$?'
        solution=f'Đầu trái của $B$ mở nên ${tex(k*a+b)}<{tex(u)}$; đầu phải đóng nên ${tex(l*a+c)}\\ge {tex(v)}$. Suy ra ${tex(left)}\\le a<{tex(right)}$, tức $S={tex(sp.FiniteSet(*vals))}$. Do $|S|={len(vals)}$, số tập con là $2^{{{len(vals)}}}={2**len(vals)}$.'
        return stem,solution,{'type':'scalar','value':str(2**len(vals))},'Chỉ nhập số tập con của S.'
    if kind=='negative_overlap':
        k,t=p['k'],p['t'];width=sp.sqrt(t/k)
        with localcontext() as ctx:
            ctx.prec=50
            rounded=Decimal(str(sp.N(width,45))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        stem=f'Cho $m<0$, $A=(-\\infty;{tex(k*m)})$, $B=(\\dfrac{{{tex(t)}}}{{m}};+\\infty)$. Biết tập các $m$ để $A\\cap B\\ne\\varnothing$ là $(a;b)$. Tính $b-a$, làm tròn đến hàng phần trăm.'
        solution=f'Hai khoảng mở giao nhau khi ${tex(k*m)}>\\dfrac{{{tex(t)}}}{{m}}$. Vì $m<0$, nhân với $m$ phải đổi chiều: ${tex(k)}m^2<{tex(t)}$. Suy ra $-{tex(width)}<m<0$, nên $b-a={tex(width)}\\approx {str(rounded).replace('.', '{,}')}$.'
        return stem,solution,{'type':'scalar','value':str(sp.Rational(str(rounded))),'display':str(rounded)},'Nhập kết quả làm tròn đến hàng phần trăm (2 chữ số thập phân), dùng dấu phẩy (,) làm dấu thập phân, ví dụ 0,67.'
    if kind=='open_subset_count':
        u,v,k,t=[p[x] for x in ('u','v','k','t')]
        left=max(sp.ceiling(u),sp.floor(t/(k-1))+1);right=(v+t)/k
        vals=integer_values(left,right)
        # Schematic positions, current endpoint labels; no stale original numbers.
        diagram=r'''\begin{tikzpicture}[scale=.8]
\draw[->] (0,1.5)--(7,1.5); \node[left] at (0,1.5) {$A$};
\draw[very thick,blue] (1,1.5)--(6,1.5);
\node at (1,1.5) {$($}; \node at (6,1.5) {$)$};
\node[above] at (1,1.7) {$LEFT$}; \node[above] at (6,1.7) {$RIGHT$};
\draw[->] (0,0)--(7,0); \node[left] at (0,0) {$B$};
\draw[very thick,red] (2,0)--(5,0); \node at (2,0) {$($}; \node at (5,0) {$)$};
\node[below] at (2,-.1) {$m$}; \node[below] at (5,-.1) {$END$};
\end{tikzpicture}'''.replace('LEFT',tex(u)).replace('RIGHT',tex(v)).replace('END',tex(k*m-t))
        stem=diagram+f'\n(Hình minh họa quan hệ bao hàm, không theo tỉ lệ.) Cho hai tập khác rỗng $A=({tex(u)};{tex(v)})$, $B=(m;{tex(k*m-t)})$. Có bao nhiêu giá trị nguyên của $m$ để $B\\subset A$?'
        solution=f'$B$ khác rỗng khi $m>{tex(t/(k-1))}$. Vì cả hai khoảng đều mở, $B\\subset A$ khi $m\\ge {tex(u)}$ và ${tex(k*m-t)}\\le {tex(v)}$. Các giá trị nguyên thỏa mãn là ${tex(sp.FiniteSet(*vals))}$; có ${len(vals)}$ giá trị.'
        return stem,solution,{'type':'scalar','value':str(len(vals))},'Chỉ nhập số giá trị nguyên của m.'
    raise ValueError('Chưa hỗ trợ dạng tập hợp này.')


def random_data(kind):
    ri=RNG.randint
    if kind=='positive_subset':return dict(u=ri(1,8),v=ri(3,18),l=ri(-8,0),k=ri(2,6),t=ri(-5,8))
    if kind=='empty_intersection':return dict(u=ri(1,8),v=ri(1,8),k=ri(2,6),l=ri(-6,0),r=ri(1,8))
    if kind=='closed_subset_count':return dict(u=ri(1,6),v=ri(1,6),k=ri(2,5),l=ri(-6,0),r=ri(8,40))
    if kind=='singleton_positive':
        r=ri(2,35);s=ri(1,r-1)
        return dict(h=r*s,t=r*r-s*s)
    if kind=='power_set_count':
        u=ri(1,10)
        return dict(u=u,v=u+ri(2,10),k=ri(2,6),p=ri(-12,2),l=ri(2,6),q=ri(4,30))
    if kind=='negative_overlap':return dict(k=ri(4,40),t=ri(1,100))
    if kind=='open_subset_count':
        u=ri(1,6);k=ri(2,6);t=ri(1,10)
        return dict(u=u,v=k*(u+ri(1,5))-t+ri(0,k-1),k=k,t=t)
    raise ValueError('Không có bộ sinh số.')


def generate(q, config, original=False):
    for _ in range(100):
        p=config['data'] if original else random_data(config['type'])
        if not original and p==config['data']:continue
        stem,solution,answer,hint=solve(config['type'],p)
        # Avoid empty sample exercises and excessively large power-set answers.
        if not original and answer['type']=='finite' and not answer['values']:continue
        if not original and answer['type']=='scalar' and config['type'].endswith('count') and not 1<=int(answer['value'])<=1024:continue
        break
    else:raise ValueError('Chưa sinh được bộ số hợp lệ.')
    out=copy.deepcopy(q)
    out.update(text=stem+'\n'+hint,solution=solution,kind='TLN',options=[],answer='')
    out['_race_variant_spec']=config
    out['_race_variant_values']={k:str(v) for k,v in p.items()}
    out['_race_set_answer']=answer
    if answer['type']=='scalar':
        out['_race_answer_components']=[answer['value']]
        out['_race_answer_display']='$'+(answer.get('display') or tex(sp.Rational(answer['value'])))+'$'
    elif answer['type']=='finite':out['_race_answer_display']='$'+tex(sp.FiniteSet(*map(sp.Rational,answer['values'])))+'$'
    else:out['_race_answer_display']='$'+tex(answer_set(answer))+'$'
    return out


def answer_set(answer):
    if answer['type']=='finite':return sp.FiniteSet(*map(sp.Rational,answer['values']))
    intervals=[sp.Interval(-sp.oo if lo=='-oo' else sp.Rational(lo),sp.oo if hi=='oo' else sp.Rational(hi),left_open=lop,right_open=rop) for lo,hi,lop,rop in answer['values']]
    return sp.Union(*intervals)


def matches(q, text):
    from race_variants import parse_expression
    answer=q['_race_set_answer']
    if not isinstance(text,str) or len(text)>1500:return False
    try:
        if answer['type']=='scalar':return abs(float(sp.N(parse_expression(text)-parse_expression(answer['value'],False),18)))<=1e-9
        text=text.strip().replace('−','-').replace('∞','inf').replace('\\infty','inf').replace('\\cup','U')
        if text.lower() in ('rỗng','rong','empty','{}','\\varnothing'):return answer_set(answer)==sp.S.EmptySet
        if answer['type']=='finite':
            parts=text.strip('{} ').replace(',',';').split(';')
            return sp.FiniteSet(*(parse_expression(p) for p in parts))==answer_set(answer)
        def bound(s):
            s=s.strip().lower()
            if s in ('inf','+inf','oo','+oo'):return sp.oo
            if s in ('-inf','-oo'):return -sp.oo
            return parse_expression(s)
        pieces=[]
        for part in re.split(r'\s*(?:U|∪)\s*',text):
            match=re.fullmatch(r'([\[(])\s*(.+?)\s*;\s*(.+?)\s*([\])])',part)
            if match:
                left,right=bound(match[2]),bound(match[3])
                if left==sp.oo or right==-sp.oo or (left==-sp.oo and match[1]!='(') or (right==sp.oo and match[4]!=')'):return False
                pieces.append(sp.Interval(left,right,left_open=match[1]=='(',right_open=match[4]==')'))
                continue
            condition=re.fullmatch(r'm\s*(>=|<=|>|<|≥|≤)\s*(.+)',part)
            if not condition:return False
            op,x=condition[1],bound(condition[2])
            pieces.append(sp.Interval(x,sp.oo,left_open=op=='>') if op in ('>=','≥','>') else sp.Interval(-sp.oo,x,right_open=op=='<'))
        return sp.Union(*pieces)==answer_set(answer)
    except (ValueError,TypeError,SyntaxError,ZeroDivisionError,OverflowError):return False
