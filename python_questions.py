"""Named Python calculation functions for practice questions."""
import ast
import copy
import math
import re
import random
from fractions import Fraction
from types import SimpleNamespace
import sympy as sp

MATH_FUNCTIONS={name:getattr(sp,name) for name in ('sqrt','sin','cos','tan','asin','acos','atan','exp','log','floor','ceiling')}
MATH_FUNCTIONS.update(ceil=sp.ceiling,fabs=sp.Abs,log10=lambda x:sp.log(x,10),radians=lambda x:x*sp.pi/180,degrees=lambda x:x*180/sp.pi)
MATH_CONSTANTS={'pi':sp.pi,'e':sp.E,'tau':2*sp.pi}
MATH=SimpleNamespace(**MATH_FUNCTIONS,**MATH_CONSTANTS)

def number(value):
    text=str(value).replace(',','.')
    if len(text)>150 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,2})?(?:/[+-]?\d+)?',text): raise ValueError('Số liệu phải là số hoặc phân số ngắn.')
    try: result=sp.Rational(text)
    except (ValueError,TypeError): raise ValueError('Số liệu phải là số hoặc phân số.') from None
    if abs(result)>1000000000 or result.q.bit_length()>128: raise ValueError('Số liệu vượt giới hạn.')
    return result

def power(a,b):
    if b.is_number is not True or b.is_real is not True or abs(b)>10: raise ValueError('Số mũ vượt giới hạn ±10.')
    if a.is_Rational and max(int(a.p).bit_length(),int(a.q).bit_length())>4096: raise ValueError('Kết quả quá lớn.')
    result=a**b
    if result.is_Rational and max(int(result.p).bit_length(),int(result.q).bit_length())>4096: raise ValueError('Kết quả quá lớn.')
    return result

def binary(op,a,b):
    for value in (a,b):
        if isinstance(value,sp.Rational) and max(int(value.p).bit_length(),int(value.q).bit_length())>4096: raise ValueError('Kết quả quá lớn.')
    result={'Add':lambda:a+b,'Sub':lambda:a-b,'Mult':lambda:a*b,'Div':lambda:a/b,'Pow':lambda:power(a,b)}[op]()
    if isinstance(result,sp.Rational) and max(int(result.p).bit_length(),int(result.q).bit_length())>4096: raise ValueError('Kết quả quá lớn.')
    if sp.count_ops(result)>100: raise ValueError('Biểu thức quá phức tạp.')
    return result

def inspect_code(source):
    if not isinstance(source,str) or not 0<len(source)<=12000: raise ValueError('Nhập mã Python, tối đa 12.000 ký tự.')
    try: module=ast.parse(source)
    except SyntaxError as e: raise ValueError(f'Lỗi Python dòng {e.lineno}: {e.msg}') from None
    if len(list(ast.walk(module)))>700: raise ValueError('Hàm quá dài.')
    functions={}
    for node in module.body:
        if isinstance(node,ast.Import) and len(node.names)==1 and node.names[0].name in {'math','random'} and not node.names[0].asname: continue
        if isinstance(node,ast.ImportFrom) and node.module=='math' and node.level==0 and all(a.name in MATH_FUNCTIONS or a.name in MATH_CONSTANTS for a in node.names) and not any(a.asname for a in node.names): continue
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str): continue
        if not isinstance(node,ast.FunctionDef): raise ValueError('Viết import math và các hàm def; thao tác nhập số thực hiện trên giao diện.')
        if node.name.startswith('_') or node.name in functions or node.name in {'abs','math'}: raise ValueError('Tên hàm không hợp lệ hoặc bị trùng.')
        if node.decorator_list or node.returns or node.args.vararg or node.args.kwarg or node.args.kwonlyargs or node.args.posonlyargs: raise ValueError('Hàm dùng tham số thông thường, không decorator hoặc *args.')
        if not (0 if node.name=='sinh_so_lieu' else 1)<=len(node.args.args)<=12 or any(a.annotation or a.arg.startswith('_') for a in node.args.args): raise ValueError('Hàm có 1–12 tham số có tên rõ ràng.')
        if len({a.arg for a in node.args.args})!=len(node.args.args): raise ValueError('Tham số bị trùng.')
        functions[node.name]=node
    if not 1<=len(functions)<=12: raise ValueError('Viết từ 1 đến 12 hàm tính.')
    imported={a.name for n in module.body if isinstance(n,ast.ImportFrom) for a in n.names}
    edges={name:set() for name in functions}
    def expression(node,known,owner):
        if owner=='sinh_so_lieu' and isinstance(node,ast.Dict):
            if not 1<=len(node.keys)<=12 or any(not isinstance(k,ast.Constant) or not isinstance(k.value,str) or not k.value.isidentifier() or k.value.startswith('_') for k in node.keys): raise ValueError('sinh_so_lieu trả về dict với tên tham số rõ ràng.')
            if len({k.value for k in node.keys})!=len(node.keys): raise ValueError('Tên số liệu bị trùng.')
            for value in node.values: expression(value,known,owner)
            return
        if owner=='sinh_so_lieu' and isinstance(node,(ast.List,ast.Tuple)):
            if not 1<=len(node.elts)<=100: raise ValueError('Danh sách sinh số có 1–100 giá trị.')
            for value in node.elts: expression(value,known,owner)
            return
        if owner=='sinh_so_lieu' and isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='random' and node.func.attr in {'choice','randint'} and not node.keywords:
            if len(node.args)!=(1 if node.func.attr=='choice' else 2): raise ValueError('Sai tham số hàm random.')
            for value in node.args: expression(value,known,owner)
            return
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            if not math.isfinite(node.value) or abs(node.value)>1000000000: raise ValueError('Hằng số quá lớn.')
            return
        if isinstance(node,ast.Name) and node.id in known: return
        if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name) and node.value.id=='math' and node.attr in MATH_CONSTANTS: return
        if isinstance(node,ast.Name) and node.id in imported and node.id in MATH_CONSTANTS: return
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd,ast.Not)):
            expression(node.operand,known,owner);return
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
            expression(node.left,known,owner);expression(node.right,known,owner);return
        if isinstance(node,ast.Compare) and len(node.ops)<=3 and all(isinstance(op,(ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.Eq,ast.NotEq)) for op in node.ops):
            for n in [node.left,*node.comparators]: expression(n,known,owner)
            return
        if isinstance(node,ast.BoolOp) and isinstance(node.op,(ast.And,ast.Or)):
            for n in node.values: expression(n,known,owner)
            return
        if isinstance(node,ast.Call) and not node.keywords and len(node.args)<=12:
            name=node.func.id if isinstance(node.func,ast.Name) else None
            math_call=isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='math' and node.func.attr in MATH_FUNCTIONS
            if name in functions: edges[owner].add(name)
            elif name!='abs' and not (name in imported and name in MATH_FUNCTIONS) and not math_call: raise ValueError('Chỉ gọi hàm tính trong mã hoặc các hàm math.')
            for n in node.args: expression(n,known,owner)
            return
        raise ValueError('Chỉ dùng số, tham số, phép tính, điều kiện và các hàm math.')
    def statements(body,known,owner):
        for n in body:
            if isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str): continue
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
                target=n.targets[0].id
                if target.startswith('_') or target in functions or target in imported or target in {'math','abs'}: raise ValueError('Tên biến không hợp lệ.')
                expression(n.value,known,owner);known.add(target)
            elif isinstance(n,ast.Return): expression(n.value,known,owner)
            elif isinstance(n,ast.If):
                expression(n.test,known,owner)
                yes=set(known);no=set(known);statements(n.body,yes,owner);statements(n.orelse,no,owner);known.update(yes & no)
            else: raise ValueError('Trong hàm dùng gán biến, if và return; không dùng vòng lặp hoặc input/print.')
    for name,node in functions.items():
        for default in node.args.defaults: expression(default,set(),name)
        statements(node.body,{a.arg for a in node.args.args},name)
        if not any(isinstance(n,ast.Return) for n in ast.walk(node)): raise ValueError('Hàm cần return kết quả.')
    def visit(name,chain):
        if name in chain: raise ValueError('Không gọi hàm đệ quy.')
        for child in edges[name]: visit(child,chain|{name})
    for name in functions: visit(name,set())
    return module,functions

def signatures(source):
    _,functions=inspect_code(source)
    return [{'name':name,'parameters':[a.arg for a in node.args.args]} for name,node in functions.items() if name!='sinh_so_lieu']

def run(source,function,values):
    module,functions=inspect_code(source)
    if function not in functions: raise ValueError('Chọn hàm cần chạy.')
    args=[a.arg for a in functions[function].args.args]
    if set(args)!=set(values): raise ValueError('Số liệu không khớp tham số của hàm.')
    class ExactNumbers(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) in (int,float):
                text=ast.get_source_segment(source,node)
                return ast.copy_location(ast.Call(func=ast.Name(id='_number',ctx=ast.Load()),args=[ast.Constant(text)],keywords=[]),node)
            return node
        def visit_BinOp(self,node):
            node=self.generic_visit(node)
            return ast.copy_location(ast.Call(func=ast.Name(id='_binary',ctx=ast.Load()),args=[ast.Constant(type(node.op).__name__),node.left,node.right],keywords=[]),node)
    module=copy.deepcopy(module)
    module.body=[n for n in module.body if isinstance(n,ast.FunctionDef)]
    module=ExactNumbers().visit(module)
    for node in module.body:
        node.body.insert(0,ast.Expr(value=ast.Call(func=ast.Name(id='_tick',ctx=ast.Load()),args=[],keywords=[])))
    module=ast.fix_missing_locations(module)
    budget=[200]
    def tick():
        budget[0]-=1
        if budget[0]<0: raise ValueError('Hàm gọi quá nhiều lần.')
    def randint(lo,hi):
        if not isinstance(lo,sp.Integer) or not isinstance(hi,sp.Integer) or lo>hi or hi-lo>100000: raise ValueError('random.randint cần khoảng số nguyên hợp lệ.')
        return sp.Integer(random.SystemRandom().randint(int(lo),int(hi)))
    namespace={'__builtins__':{},'random':SimpleNamespace(choice=random.SystemRandom().choice,randint=randint),'math':MATH,'abs':sp.Abs,'_number':number,'_binary':binary,'_tick':tick}
    namespace.update(MATH_FUNCTIONS);namespace.update(MATH_CONSTANTS)
    try:
        exec(compile(module,'<physics-function>','exec'),namespace)
        result=namespace[function](**{name:number(values[name]) for name in args})
        if function=='sinh_so_lieu':
            if not isinstance(result,dict) or not result: raise ValueError('sinh_so_lieu phải trả về dict số liệu.')
            return {name:number(value) for name,value in result.items()}
        if not isinstance(result,sp.Expr) or result.is_number is not True or result.is_real is not True or result.is_finite is not True or sp.count_ops(result)>100: raise ValueError('Hàm phải trả về một kết quả số thực hữu hạn.')
        return sp.simplify(result)
    except (TypeError,NameError,ZeroDivisionError,OverflowError) as exc: raise ValueError('Không chạy được hàm: '+str(exc)) from None

def validate_config(q,c):
    from variable_templates import slots
    _,functions=inspect_code(c.get('python_code',''))
    target=c.get('function_name')
    if target not in functions: raise ValueError('Chọn hàm tính của câu.')
    args=[a.arg for a in functions[target].args.args]
    if target=='sinh_so_lieu': raise ValueError('Chọn hàm tính đáp án, không chọn hàm sinh số.')
    if 'sinh_so_lieu' in functions:
        if functions['sinh_so_lieu'].args.args: raise ValueError('sinh_so_lieu không nhận tham số.')
        generated=run(c['python_code'],'sinh_so_lieu',{})
        if set(generated)!=set(args): raise ValueError('Tên trong dict sinh_so_lieu phải khớp tham số hàm tính.')
    ps=c.get('parameters')
    if not isinstance(ps,list) or any(not isinstance(p,dict) for p in ps) or [p.get('argument') for p in ps]!=args: raise ValueError('Thiếu tham số của hàm.')
    known={s['name']:s for s in slots(q['text'])};used=set()
    for p in ps:
        slot=p.get('slot')
        if slot:
            if slot not in known or slot in used: raise ValueError('Mỗi số trong đề chỉ gắn với một tham số.')
            used.add(slot)
        number(p.get('original',''))
        lo,hi,step=(number(p.get(k,'')) for k in ('min','max','step'))
        if lo>hi or step<=0 or (hi-lo)/step>10000: raise ValueError('Khoảng số hoặc bước không hợp lệ.')
    replacements=c.get('replacements',[])
    if not isinstance(replacements,list) or len(replacements)>20: raise ValueError('Số phụ thuộc không hợp lệ.')
    for r in replacements:
        if not isinstance(r,dict) or r.get('slot') not in known or r['slot'] in used: raise ValueError('Số phụ thuộc bị trùng.')
        used.add(r['slot'])
        from variable_templates import evaluate
        evaluate(r.get('expression',''),{p['argument']:Fraction(str(number(p['original']))) for p in ps})
    if not used: raise ValueError('Gắn ít nhất một tham số với số trong đề.')
    for key in ('answer_template','solution_template'):
        if not isinstance(c.get(key),str) or not c[key].strip() or len(c[key])>5000: raise ValueError('Điền mẫu đáp án và lời giải.')
    if '{answer}' not in c['answer_template']: raise ValueError('Mẫu đáp án cần {answer}.')
    if q['kind']=='TN' and (not isinstance(c.get('distractors'),list) or len(c['distractors'])!=3): raise ValueError('Cần 3 công thức phương án nhiễu.')
    return c

def latex(value):
    from variable_templates import tex_number
    if value.is_Rational: return tex_number(Fraction(str(value)))
    return sp.latex(value)

def render(template,values):
    for name,value in values.items(): template=template.replace('{'+name+'}',latex(value))
    return template

def arithmetic(source,values):
    # Distractors and dependent values use the same numeric functions, never eval strings.
    names=list(values)
    code='def ket_qua('+','.join(names)+'):\n    return '+source+'\n'
    module,_=inspect_code(code)
    # run accepts rational inputs; symbolic answer is already safe and evaluated here.
    if any(not v.is_Rational for v in values.values()):
        import re
        # Only answer multiples/sign changes are needed for radical answers.
        match=re.fullmatch(r'(-?answer|answer\s*([*/+-])\s*(-?\d+(?:\.\d+)?))',source.strip())
        if not match: raise ValueError('Đáp án có căn/π: dùng -answer hoặc answer * / + - một số.')
        if source.strip()=='answer': return values['answer']
        if source.strip()=='-answer': return -values['answer']
        b=number(match[3]);a=values['answer']
        return {'*':lambda:a*b,'/':lambda:a/b,'+':lambda:a+b,'-':lambda:a-b}[match[2]]()
    return run(code,'ket_qua',values)

def generate(q,c,original=False,overrides=None):
    from variable_templates import slots,RNG
    validate_config(q,c)
    values={}
    replacements={}
    generated=None
    if not original and overrides is None and 'sinh_so_lieu' in inspect_code(c['python_code'])[1]:
        generated=run(c['python_code'],'sinh_so_lieu',{})
    for p in c['parameters']:
        lo,hi,step=(number(p[k]) for k in ('min','max','step'))
        value=number(p['original']) if original else lo+step*RNG.randint(0,int((hi-lo)/step))
        if generated is not None: value=generated[p['argument']]
        if overrides is not None: value=number(overrides[p['argument']])
        values[p['argument']]=value
        if p.get('slot'): replacements[p['slot']]=value
    for r in c.get('replacements',[]): replacements[r['slot']]=arithmetic(r['expression'],values)
    if original:
        old={s['name']:number(s['value']) for s in slots(q['text'])}
        if any(value!=old[name] for name,value in replacements.items()): raise ValueError('Tham số hoặc quan hệ không khớp số liệu gốc trong đề.')
    answer=run(c['python_code'],c['function_name'],values)
    stem=q['text']
    for slot in reversed(slots(stem)):
        if slot['name'] in replacements: stem=stem[:slot['start']]+latex(replacements[slot['name']])+stem[slot['end']:]
    values['answer']=answer
    options=[]
    if q['kind']=='TN':
        candidates=[answer]+[sp.simplify(arithmetic(x,{'answer':answer})) for x in c['distractors']]
        if any(v.is_real is not True or v.is_finite is not True for v in candidates) or len(set(candidates))!=4: raise ValueError('Phương án nhiễu trùng hoặc không hợp lệ.')
        options=[{'text':render(c['answer_template'],{**values,'answer':v}),'correct':i==0} for i,v in enumerate(candidates)]
        RNG.shuffle(options)
    elif c['answer_template'].strip()!='{answer}': raise ValueError('Trả lời ngắn dùng mẫu {answer}.')
    return {'text':stem,'solution':render(c['solution_template'],values),'answer':str(answer),'answer_text':('$'+latex(answer)+'$') if q['kind']=='TLN' else render(c['answer_template'],values),'options':options,'kind':q['kind'],'formula':c['function_name']+'('+', '.join(p['argument'] for p in c['parameters'])+')','figure':{'amplitude':None},'params':[str(v) for k,v in values.items() if k!='answer'],'html':True,'python_function':True}


def same_answer(text,expected):
    def parse(value):
        value=str(value).strip().replace(',', '.').replace('^','**')
        if len(value)>100: raise ValueError('Biểu thức quá dài.')
        code='import math\nfrom math import '+','.join(sorted(MATH_FUNCTIONS))+',pi,e,tau\ndef ket_qua(dummy):\n    return '+value+'\n'
        return run(code,'ket_qua',{'dummy':'0'})
    return sp.simplify(parse(text)-parse(expected))==0
