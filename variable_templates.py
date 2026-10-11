"""Per-question numeric slots and exact, restricted arithmetic formulas."""
import ast
import hashlib
import json
import re
from fractions import Fraction
from random import SystemRandom
from pathlib import Path
from dynamic_engine import exact, fraction

RNG=SystemRandom()
MATH=re.compile(r'(?<!\\)\$\$[\s\S]*?(?<!\\)\$\$|(?<!\\)\$[^$]*?(?<!\\)\$')
NUMBER=re.compile(r'\d+(?:(?:\{,\}|[.,])\d+)?')

def slots(text):
    result=[]
    for segment in MATH.finditer(text):
        for m in NUMBER.finditer(segment.group()):
            raw=m.group()
            result.append({'name':'v'+str(len(result)), 'raw':raw,'value':str(fraction(raw.replace('{,}', '.'))), 'start':segment.start()+m.start(),'end':segment.start()+m.end(),'context':segment.group()})
    if len(result)>40: raise ValueError('Câu có quá nhiều số; chọn một câu ngắn hơn.')
    return result

def identity(q):
    # Content identity survives reordering and disambiguates duplicated or missing IDs.
    body=json.dumps([q.get('src',''),q.get('kind'),q.get('text'),q.get('options'),q.get('answer')],ensure_ascii=False,sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()[:32]

def location(q):
    src=q.get('src','')
    return src.rsplit('/',1)[0]+'/_dynamic/'+identity(q)+'.json'

def evaluate(expression,values):
    if not isinstance(expression,str) or not 0<len(expression)<=300: raise ValueError('Công thức rỗng hoặc quá dài.')
    try: tree=ast.parse(expression,mode='eval')
    except SyntaxError: raise ValueError('Công thức không hợp lệ.') from None
    if len(list(ast.walk(tree)))>100: raise ValueError('Công thức quá phức tạp.')
    def visit(n):
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):
            value=fraction(ast.get_source_segment(expression,n))
        elif isinstance(n,ast.Name) and n.id in values: value=values[n.id]
        elif isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.USub,ast.UAdd)):
            value=visit(n.operand);value=-value if isinstance(n.op,ast.USub) else value
        elif isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Add): value=a+b
            elif isinstance(n.op,ast.Sub): value=a-b
            elif isinstance(n.op,ast.Mult): value=a*b
            elif isinstance(n.op,ast.Div): value=a/b
            else:
                if b.denominator!=1 or abs(b)>10: raise ValueError('Số mũ phải là số nguyên từ −10 đến 10.')
                value=a**int(b)
        elif isinstance(n,ast.Compare) and len(n.ops)==1:
            a,b=visit(n.left),visit(n.comparators[0]);op=n.ops[0]
            if isinstance(op,ast.LtE): return a<=b
            if isinstance(op,ast.Lt): return a<b
            if isinstance(op,ast.GtE): return a>=b
            if isinstance(op,ast.Gt): return a>b
            if isinstance(op,ast.Eq): return a==b
            raise ValueError('Điều kiện không hợp lệ.')
        else: raise ValueError('Chỉ dùng biến, số, + − * / ** và phép so sánh; không gọi hàm.')
        if not isinstance(value,Fraction) or max(value.numerator.bit_length(),value.denominator.bit_length())>256: raise ValueError('Kết quả vượt giới hạn.')
        return value
    return visit(tree.body)

def validate(q,config):
    if q.get('kind') not in {'TN','TLN'}: raise ValueError('Hiện hỗ trợ câu tính toán TN và trả lời ngắn.')
    if not isinstance(config,dict): raise ValueError('Cấu hình không hợp lệ.')
    known={v['name']:v for v in slots(q['text'])}
    selected=config.get('variables',[])
    if not isinstance(selected,list) or not 1<=len(selected)<=20: raise ValueError('Chọn từ 1 đến 20 số để đổi.')
    names=set()
    for v in selected:
        if not isinstance(v,dict) or v.get('name') not in known or v['name'] in names: raise ValueError('Biến không hợp lệ hoặc trùng.')
        names.add(v['name'])
        relation=v.get('relation','')
        if relation:
            if not isinstance(relation,str) or len(relation)>300: raise ValueError('Quan hệ biến không hợp lệ.')
        else:
            lo,hi,step=(fraction(v.get(k,'')) for k in ('min','max','step'))
            if not -10000<=lo<=hi<=10000 or step<=0 or (hi-lo)/step>10000: raise ValueError('Khoảng số hoặc bước thay đổi không hợp lệ.')
    for k in ('formula','answer_template','solution_template'):
        if not isinstance(config.get(k),str) or not config[k].strip() or len(config[k])>5000: raise ValueError('Điền công thức, mẫu đáp án và mẫu lời giải.')
    if '{answer}' not in config['answer_template']: raise ValueError('Mẫu đáp án cần có {answer}.')
    if q['kind']=='TN' and (not isinstance(config.get('distractors'),list) or len(config['distractors'])!=3): raise ValueError('Cần 3 công thức phương án nhiễu.')
    return config

def tex_number(value):
    value=fraction(value)
    if value.denominator!=1 and '/' in exact(value): return r'\frac{'+str(value.numerator)+'}{'+str(value.denominator)+'}'
    return exact(value).replace(',', '{,}')

def render(template,values):
    if not isinstance(template,str): raise ValueError('Mẫu văn bản không hợp lệ.')
    for name,value in values.items(): template=template.replace('{'+name+'}',tex_number(value))
    if re.search(r'\{(?:v\d+|answer)\}',template): raise ValueError('Mẫu dùng biến chưa được khai báo.')
    return template

def generate_custom(q,config,original=False):
    config=validate(q,config)
    numbered=slots(q['text'])
    values=saved_function_values(q,config,original)
    answer=values['answer']
    if type(answer) is bool: raise ValueError('Công thức đáp án phải trả về số.')
    values['answer']=answer
    stem=q['text']
    for slot in reversed(numbered):
        if slot['name'] in values:
            stem=stem[:slot['start']]+tex_number(values[slot['name']])+stem[slot['end']:]
    answer_text=render(config['answer_template'],values)
    options=[]
    if q['kind']=='TN':
        candidates=[answer]+[evaluate(x,values) for x in config['distractors']]
        if any(type(x) is bool for x in candidates) or len(set(candidates))!=4: raise ValueError('Bốn phương án bị trùng; chỉnh công thức nhiễu.')
        options=[{'text':render(config['answer_template'],{**values,'answer':v}),'correct':i==0} for i,v in enumerate(candidates)]
        RNG.shuffle(options)
    elif config['answer_template'].strip()!='{answer}':
        raise ValueError('Trả lời ngắn dùng mẫu {answer}; phần đơn vị đặt trong đề.')
    return {'text':stem,'solution':render(config['solution_template'],values),'answer':exact(answer),'answer_text':answer_text,'options':options,'kind':q['kind'],'formula':config['formula'],'figure':{'amplitude':None},'params':[exact(v) for k,v in values.items() if k!='answer'],'html':True}

def function_name(q):
    label=re.sub(r'[^A-Za-z0-9_]', '_', str(q.get('id') or ''))[:60]
    return 'cau_'+(label+'_' if label else '')+identity(q)[:12]

def expression_source(expression,values):
    evaluate(expression,values)  # Validate before generating executable syntax.
    tree=ast.parse(expression,mode='eval')
    class ExactConstants(ast.NodeTransformer):
        def visit_Constant(self,node):
            return ast.copy_location(ast.Call(func=ast.Name(id='Fraction',ctx=ast.Load()),args=[ast.Constant(value=ast.get_source_segment(expression,node))],keywords=[]),node)
    return ast.unparse(ast.fix_missing_locations(ExactConstants().visit(tree)))

def source_code(q,config):
    validate(q,config)
    originals={s['name']:fraction(s['value']) for s in slots(q['text'])}
    validation_values={}
    lines=['def '+function_name(q)+'(dung_so_goc=False):','    for _ in range(100):']
    for v in config['variables']:
        name=v['name']
        if v.get('relation'):
            expr=expression_source(v['relation'],validation_values)
        else:
            lo,hi,step=(fraction(v[k]) for k in ('min','max','step'))
            expr=f"Fraction({str(lo)!r}) + Fraction({str(step)!r}) * randint(0, {int((hi-lo)/step)})"
        validation_values[name]=originals[name]
        lines.append(f"        {name} = Fraction({str(originals[name])!r}) if dung_so_goc else ({expr})")
    if config.get('condition'):
        condition=expression_source(config['condition'],validation_values)
        lines.extend(['        if not ('+condition+'):',"            if dung_so_goc: raise ValueError('Số liệu gốc không thỏa điều kiện.')",'            continue'])
    answer=expression_source(config['formula'],validation_values)
    lines.append('        answer = '+answer)
    items=[repr(v['name'])+': '+v['name'] for v in config['variables']]+["'answer': answer"]
    lines.extend(['        return {'+', '.join(items)+'}',"    raise ValueError('Không sinh được bộ số hợp lệ.')"])
    return '\n'.join(lines)+'\n'

def saved_function_values(q,config,original):
    from app import ROOT
    file=ROOT/(q['src'].rsplit('/',1)[0]+'/luyen_tap.py')
    expected=source_code(q,config)
    if file.is_file() and load_config(q)==config:
        module=file.read_text(encoding='utf-8')
        start='# BEGIN '+identity(q)+'\n';end='# END '+identity(q)
        if start not in module or end not in module: raise ValueError('File bài luyện tập chưa có hàm của câu này.')
        saved=module.split(start,1)[1].split(end,1)[0]
        if saved!=expected: raise ValueError('Mã hàm không khớp cấu hình đã lưu; lưu lại mẫu.')
    else:
        saved=expected  # Used only for a preview before the initial save.
    namespace={'__builtins__':{},'Fraction':Fraction,'randint':RNG.randint,'range':range,'ValueError':ValueError}
    exec(compile(saved,'<verified-numeric-template>','exec'),namespace)
    return namespace[function_name(q)](original)

def load_config(q):
    from app import ROOT
    p=ROOT/location(q)
    if not p.is_file(): return None
    try:
        config=json.loads(p.read_text(encoding='utf-8'))['config']
        validate(q,config)
        return config
    except (ValueError,KeyError,TypeError): return None


def register(app):
    from flask import request, jsonify, redirect
    def get_question(src,idx):
        from app import _safe_repo_file,read_tex,parse_questions
        p,_=_safe_repo_file(src)
        _,tex=read_tex(p)
        qs=parse_questions(tex)
        if type(idx) is not int or not 0<=idx<len(qs): raise ValueError('Không tìm thấy câu gốc.')
        q=qs[idx];q['src']=p;q['file_idx']=idx
        return q

    @app.get('/api/variable-template')
    def get_template():
        from app import can_manage_bank,question_payload
        if not can_manage_bank(): return jsonify(ok=False,error='Chỉ ADMIN được cấu hình mẫu.'),403
        try:
            q=get_question(request.args.get('src',''),int(request.args.get('file_idx','-1')))
            payload=question_payload(q)
            correct=next((o['text'] for o in payload.get('options',[]) if o['correct']),payload.get('answer',''))
            return jsonify(ok=True,slots=slots(q['text']),text=q['text'],id=q.get('id',''),correct=correct,kind=q['kind'],config=load_config(q))
        except (ValueError,TypeError): return jsonify(ok=False,error='Không đọc được câu.'),400

    @app.post('/api/variable-template/preview')
    @app.post('/api/variable-template/save')
    def preview_save():
        from app import can_manage_bank,html_question,github_put_text,github_file_sha,_safe_repo_file
        if not can_manage_bank(): return jsonify(ok=False,error='Chỉ ADMIN được cấu hình mẫu.'),403
        try:
            data=request.get_json(silent=True) or {}
            q=get_question(data.get('src',''),data.get('file_idx'))
            config=validate(q,data.get('config'))
            original=generate_custom(q,config,True)
            for _ in range(20): generate_custom(q,config)
            generated=generate_custom(q,config)
            def view(exercise):
                return {'text':html_question(exercise['text'],q['src']),'answer':html_question(exercise['answer_text'],q['src']),'solution':html_question(exercise['solution'],q['src'])}
            if request.path.endswith('/save'):
                if data.get('confirm_original') is not True: raise ValueError('Đối chiếu đáp án gốc rồi tích xác nhận trước khi lưu.')
                path=location(q)
                record={'question_id':q.get('id',''),'source':q['src'],'fingerprint':identity(q),'config':config,'python_source':source_code(q,config)}
                text=json.dumps(record,ensure_ascii=False,indent=2)
                # GitHub is the durable source; report success only after the commit.
                from app import gh_api,BRANCH
                import urllib.parse,base64
                branch=urllib.parse.quote(BRANCH,safe='')
                head=gh_api('git/ref/heads/'+branch)['object']['sha']
                base_tree=gh_api('git/commits/'+head)['tree']['sha']
                py_path=q['src'].rsplit('/',1)[0]+'/luyen_tap.py'
                _,py_local=_safe_repo_file(py_path)
                try:
                    remote=gh_api('contents/'+urllib.parse.quote(py_path,safe='/')+'?ref='+head)
                    module=base64.b64decode(remote['content']).decode('utf-8')
                except RuntimeError as exc:
                    if '404' not in str(exc): raise
                    module='"""Hàm luyện tập riêng cho các câu trong bài. Không dùng AI khi đổi số."""\nfrom fractions import Fraction\nfrom random import randint\n\n'
                start='# BEGIN '+identity(q)+'\n';end='# END '+identity(q)+'\n'
                block=start+source_code(q,config)+end
                if start in module and end in module:
                    prefix,rest=module.split(start,1);_,suffix=rest.split(end,1);module=prefix+block+suffix
                else: module+='\n'+block
                tree=gh_api('git/trees','POST',{'base_tree':base_tree,'tree':[{'path':p,'mode':'100644','type':'blob','content':t} for p,t in [(path,text),(py_path,module)]]})['sha']
                commit=gh_api('git/commits','POST',{'message':'Lưu hàm đổi biến cho '+str(q.get('id') or identity(q)),'tree':tree,'parents':[head]})['sha']
                gh_api('git/refs/heads/'+branch,'PATCH',{'sha':commit,'force':False})
                _,local=_safe_repo_file(path);local.parent.mkdir(parents=True,exist_ok=True);local.write_text(text,encoding='utf-8')
                py_local.parent.mkdir(parents=True,exist_ok=True);py_local.write_text(module,encoding='utf-8')
            return jsonify(ok=True,original=view(original),example=view(generated),code=source_code(q,config),saved=request.path.endswith('/save'))
        except (ValueError,TypeError,KeyError,ZeroDivisionError,SyntaxError): return jsonify(ok=False,error='Cấu hình không hợp lệ. Kiểm tra biến, khoảng số, công thức, điều kiện và phương án nhiễu.'),400
        except RuntimeError: return jsonify(ok=False,error='Chưa lưu được lên GitHub. Kiểm tra kết nối GitHub của máy chủ.'),502

    @app.get('/member/variable-builder')
    def builder_page():
        from app import can_manage_bank,page,login_url
        if not can_manage_bank(): return redirect(login_url(request.full_path))
        return page('Đổi biến bằng Python', '''<section id="vb"><h2>🐍 Tạo hàm đổi biến cho câu này</h2><p>Mỗi bài lưu một file <b>luyen_tap.py</b> cạnh de.tex; mỗi câu có một hàm tính riêng trong file đó.</p><p>Chọn số trong $…$ hoặc $$…$$ được phép đổi; số bỏ chọn được giữ nguyên. Công thức dùng v0, v1… và + − * / **.</p><pre id="vbStem"></pre><div id="vbVariables"></div><label>Công thức tính đáp án (hoặc hệ số)<input id="vbFormula" placeholder="-v1**2*v3"></label><label>Điều kiện (tùy chọn)<input id="vbCondition" placeholder="v3**2*3 <= v0**2"></label><label>Mẫu đáp án: dùng {answer}<input id="vbAnswer" placeholder="$ {answer}\\pi^2\\sqrt{3}\\,\\mathrm{cm/s^2} $"></label><label>Mẫu lời giải<textarea id="vbSolution"></textarea></label><label>Ba công thức nhiễu, mỗi dòng một công thức<textarea id="vbDistractors">answer*2
answer/2
-answer</textarea></label><button id="vbPreview" type="button">Chạy thử và xem hàm</button><div id="vbOutput"></div><label><input id="vbConfirm" type="checkbox"> Tôi đã đối chiếu kết quả từ số liệu gốc với đáp án gốc.</label><button id="vbSave" type="button">Lưu hàm cho câu này</button><p id="vbStatus" role="status"></p><pre id="vbCode"></pre><a id="vbPractice" class="btn" hidden>Mở bài đổi số bằng Python</a></section><style>#vb{max-width:1000px;margin:16px auto;padding:16px}#vb label{display:block;margin:10px 0}#vb input:not([type=checkbox]),#vb textarea{box-sizing:border-box;padding:8px;width:100%}#vb textarea{min-height:75px}.vb-row{display:grid;grid-template-columns:40px 1fr repeat(3,90px) 150px;gap:8px;align-items:center;margin:8px 0}#vb pre{overflow:auto;padding:12px;background:#102137;color:#e3edfb;white-space:pre-wrap}#vb button{padding:10px;margin:8px;border-radius:7px}#vbOutput{line-height:1.7;border:1px solid #abc;padding:12px} @media(max-width:700px){.vb-row{grid-template-columns:30px 1fr 1fr}.vb-row input{min-width:0}}</style><script src="/static/variable-builder.js"></script>''')
