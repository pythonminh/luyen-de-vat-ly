"""Checked generators for two exact bank questions; no text-only number replacement."""
import copy
import hashlib
import json
import random
import re
import sympy as sp
RNG = random.SystemRandom()
REGISTRY = {'472222ade8502d634682b67825df4fcfdc650806ad3792969ce89437f962ab03':'point_region',
            '7b8c9e880157f093ab86fd8eb5f78fe86e8118d6709dbf473f5287078ddb2e85':'recognize'}
x,y=sp.symbols('x y')
def spec(q):
    if q.get('kind') != 'DS' or len(q.get('statements',[])) != 4: return None
    data=[q.get('text','')]+[s.get('text','') for s in q['statements']]
    key=hashlib.sha256(re.sub(r'\s+','',json.dumps(data,ensure_ascii=False)).encode()).hexdigest()
    kind=REGISTRY.get(key)
    return {'engine':'linear_ds','type':kind} if kind else None

def generate(q, config, original=False):
    out=copy.deepcopy(q)
    if original:
        if config['type']=='recognize':
            out['statements'][3]['correct']=True
            out['solution'] = 'a) Sai: có $x^2,y^2$. b) Sai: có $y^3$. c) Đúng: $x-y$ bậc nhất. d) Đúng: hệ số của y là hằng số $-5^2=-25$, không phải lũy thừa của ẩn y; đây là bất phương trình bậc nhất hai ẩn.'
        return out
    a=RNG.choice([i for i in range(-9,10) if i]);b=RNG.choice([i for i in range(-9,10) if i])
    c=a*b*RNG.choice([-5,-4,-3,-2,-1,1,2,3,4,5])
    lower=RNG.choice([True,False]);op=r'\leq' if lower else r'\geq'
    expr=a*x+b*y+c; formula=sp.latex(expr); statements=[]; explanations=[]
    def add(text, correct, explanation):
        statements.append({'text':text,'correct':bool(correct)})
        explanations.append(('Đúng' if correct else 'Sai')+': '+explanation)
    if config['type']=='point_region':
        out['text']='Cho bất phương trình bậc nhất hai ẩn $'+formula+' '+op+' 0$.'
        points=[(RNG.randint(-12,12),RNG.randint(-12,12)) for _ in range(2)]
        for i,(u,v) in enumerate(points):
            value=a*u+b*v+c; inside=value<=0 if lower else value>=0
            claim=RNG.choice([True,False])
            add(f'$({u};{v})$ '+('là' if claim else 'không là')+' nghiệm của bất phương trình đã cho.',inside==claim,
                f'Thay $x={u},y={v}$ được ${a}\\cdot({u})+({b})\\cdot({v})+({c})={value}$. Điểm này '+('thuộc' if inside else 'không thuộc')+' miền nghiệm.')
        ax=-c//b; bx=-c//a; shift=RNG.choice([0,0,-2,-1,1,2]); aa=ax+shift;bb=bx+shift
        add(f'Đường thẳng $d: {formula}=0$ đi qua $A(0;{aa})$ và $B({bb};0)$.',b*aa+c==0 and a*bb+c==0,
            f'Thay A được ${b}\\cdot({aa})+({c})={b*aa+c}$; thay B được ${a}\\cdot({bb})+({c})={a*bb+c}$. Cả hai điểm thuộc d khi cả hai giá trị bằng 0.')
        contains=c<=0 if lower else c>=0;claim=RNG.choice([True,False])
        add('Miền nghiệm là nửa mặt phẳng kể cả bờ $'+formula+'=0$, '+('chứa' if claim else 'không chứa')+' gốc tọa độ O.',contains==claim,
            f'Bất phương trình không nghiêm ngặt nên lấy cả bờ. Thay O được ${c}$; do đó miền nghiệm '+('chứa' if contains else 'không chứa')+' O.')
        out['_race_linear_data']={'type':'point_region','a':a,'b':b,'c':c,'lower':lower,'points':points,'A':[0,aa],'B':[bb,0],'origin_claim':claim}
    else:
        out['text']='Xét các bất phương trình sau. Mỗi ý khẳng định bất phương trình đó là bất phương trình bậc nhất hai ẩn. Chọn Đúng hoặc Sai.'
        forms=[a*x**RNG.randint(2,4)+b*y**2, a*x+b*y**RNG.randint(2,4), a*x+b*y, sp.Rational(a,RNG.randint(2,9))*x-b*b*y]
        bounds=[RNG.randint(-20,20) for _ in range(3)]+[-sp.sqrt(RNG.randint(2,30))]
        records=[]
        entries=list(zip(forms,bounds)); RNG.shuffle(entries)
        for form,bound in entries:
            relation=RNG.choice([r'\leq',r'\geq','<','>']);poly=sp.Poly(form,x,y)
            linear=poly.total_degree()==1
            add('$'+sp.latex(form)+' '+relation+' '+sp.latex(bound)+'$',linear,
                '$'+sp.latex(form)+'$ '+('có dạng $ax+by$ với a, b không đồng thời bằng 0. Hệ số là hằng số dù có phân số hoặc lũy thừa của một số.' if linear else 'có lũy thừa của ẩn lớn hơn 1, nên không phải biểu thức bậc nhất hai ẩn.'))
            records.append(str(form))
        out['_race_linear_data']={'type':'recognize','forms':records}
    out['statements']=statements
    out['solution']='\n\n'.join(chr(97+i)+') '+t for i,t in enumerate(explanations))
    out['_race_variant_spec']=config
    out.pop('raw',None)
    return out
