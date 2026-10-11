import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sympy as sp
import app as portal
import python_questions as pyq
import variable_templates as vt
import dynamic_practice as dp

class PythonFunctionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path='ngan-hang/Vật lý/Lớp 11/Chương I. Dao động/L11C1 Bài 3. Vận tốc, gia tốc trong dao động điều hòa/de.tex'
        cls.tex=(portal.ROOT/cls.path).read_text()
        cls.q=next(q.copy() for q in portal.parse_questions(cls.tex) if q.get('id')=='L11C1B3-31-TN')
        cls.q.update(src=cls.path,file_idx=cls.q['idx'])
        cls.c=vt.load_config(cls.q)

    def test_saved_generator_controls_numbers(self):
        c=copy.deepcopy(self.c)
        c['python_code']='import math\nimport random\ndef sinh_so_lieu():\n    return {"bien_do": random.choice([7]), "he_so_omega": random.randint(3, 3)}\ndef tinh_gia_toc(bien_do, he_so_omega):\n    return -(he_so_omega * math.pi)**2 * bien_do * math.sqrt(3) / 2\n'
        ex=pyq.generate(self.q,c)
        self.assertEqual(ex['params'],['7','3'])
        self.assertEqual(ex['answer'],str(-sp.Rational(63,2)*sp.sqrt(3)*sp.pi**2))
        self.assertEqual(pyq.generate(self.q,c,True)['params'],['5','2'])
        self.assertEqual(pyq.generate(self.q,c,overrides={'bien_do':'4','he_so_omega':'1'})['params'],['4','1'])
        c['python_code']=c['python_code'].replace('"bien_do":','"wrong":')
        with self.assertRaises(ValueError): pyq.generate(self.q,c)

    def test_teacher_functions_and_exact_math(self):
        code='''import math

def tinh_dong_nang(khoi_luong, v):
    return 0.5 * khoi_luong * v**2

def tinh_the_nang(khoi_luong, g, h):
    return khoi_luong * g * h

def tinh_co_nang(khoi_luong, v, g, h):
    dong_nang = tinh_dong_nang(khoi_luong, v)
    the_nang = tinh_the_nang(khoi_luong, g, h)
    return dong_nang + the_nang

def tinh_v(co_nang, khoi_luong):
    return math.sqrt(2 * co_nang / khoi_luong)
'''
        self.assertEqual(pyq.signatures(code)[0],{'name':'tinh_dong_nang','parameters':['khoi_luong','v']})
        self.assertEqual(pyq.run(code,'tinh_dong_nang',{'khoi_luong':'0.2','v':'3'}),sp.Rational(9,10))
        self.assertEqual(pyq.run(code,'tinh_co_nang',{'khoi_luong':'.2','v':'3','g':'10','h':'2'}),sp.Rational(49,10))
        self.assertEqual(pyq.run(code,'tinh_v',{'co_nang':'3','khoi_luong':'2'}),sp.sqrt(3))
        self.assertTrue(pyq.same_answer('sqrt(3)/2',str(sp.sqrt(3)/2)))
        self.assertTrue(pyq.same_answer('0,9','9/10'))
        self.assertTrue(pyq.same_answer('cos(1)',str(sp.cos(1))))
        self.assertFalse(pyq.same_answer('0.3333','1/3'))

    def test_saved_native_function_and_random_questions(self):
        self.assertEqual(self.c['mode'],'python')
        self.assertIn('def tinh_gia_toc(bien_do, he_so_omega)',vt.verified_source(self.q,self.c))
        original=vt.generate_custom(self.q,self.c,True)
        self.assertEqual(pyq.run(self.c['python_code'],'tinh_gia_toc',{'bien_do':'5','he_so_omega':'2'}),-10*sp.pi**2*sp.sqrt(3))
        for _ in range(100):
            ex=vt.generate_custom(self.q,self.c)
            A,w=map(sp.Rational,ex['params'])
            self.assertEqual(pyq.run(self.c['python_code'],'tinh_gia_toc',{'bien_do':str(A),'he_so_omega':str(w)}),-w**2*A*sp.sqrt(3)*sp.pi**2/2)
            self.assertIn(r'\dfrac{\pi}{2}',ex['text'])
            self.assertIn(r'\sqrt{3}',ex['text'])
            self.assertEqual(len({o['text'] for o in ex['options']}),4)
            self.assertEqual(sum(o['correct'] for o in ex['options']),1)
        c=copy.deepcopy(self.c);c['parameters'][0]['original']='6'
        with self.assertRaises(ValueError): vt.generate_custom(self.q,c,True)

    def test_invalid_code_cannot_access_server(self):
        for code in ['import os\ndef f(x):\n    return x','def f(x):\n    return open(x)','def f(x):\n    return x.__class__','def f(x):\n    return f(x)','def f(x):\n    while True:\n        pass','def f(x):\n    return __import__(x)','def f(x):\n    return math.__dict__','def f(x):\n    return [x]']:
            with self.assertRaises(ValueError): pyq.inspect_code(code)
        with self.assertRaises(ValueError): pyq.run('def f(x):\n    return x**100','f',{'x':'2'})
        with self.assertRaises(ValueError): pyq.same_answer("__import__('os')",'1')
        with self.assertRaises(ValueError): pyq.run('def f(x):\n'+'    x = x*x\n'*20+'    return x','f',{'x':'10000'})

    def test_admin_editor_run_save_and_student_check(self):
        client=portal.app.test_client()
        with patch.object(portal,'can_manage_bank',return_value=False):
            self.assertEqual(client.post('/api/variable-template/python-functions',json={'code':self.c['python_code']}).status_code,403)
            self.assertEqual(client.post('/api/variable-template/run',json={}).status_code,403)
        with patch.object(portal,'can_manage_bank',return_value=True),patch.object(portal,'page',side_effect=lambda title,body:body),patch.object(portal,'read_tex',return_value=(self.path,self.tex)):
            page=client.get('/member/variable-builder',query_string={'src':self.path,'file_idx':self.q['file_idx']})
            self.assertIn('id="vbPythonCode"',page.text)
            self.assertNotIn('id="vbFormula"',page.text)
            funcs=client.post('/api/variable-template/python-functions',json={'code':self.c['python_code']}).get_json()
            self.assertEqual(funcs['functions'][0]['parameters'],['bien_do','he_so_omega'])
            r=client.post('/api/variable-template/run',json={'src':self.path,'file_idx':self.q['file_idx'],'config':self.c,'values':{'bien_do':'8','he_so_omega':'3'}})
            self.assertEqual(r.status_code,200,r.text)
            self.assertIn('36',r.get_json()['answer'])
            preview=client.post('/api/variable-template/preview',json={'src':self.path,'file_idx':self.q['file_idx'],'config':self.c})
            self.assertEqual(preview.status_code,200,preview.text)
            self.assertIn('def tinh_gia_toc',preview.get_json()['code'])
        import base64
        def github(path,method='GET',payload=None):
            if path.startswith('git/ref/'):return {'object':{'sha':'parent'}}
            if path=='git/commits/parent':return {'tree':{'sha':'base'}}
            if path.startswith('contents/'):return {'content':base64.b64encode(b'def cau_khac(x):\n    return x\n').decode()}
            if path=='git/trees':self.assertIn(self.c['python_code'],payload['tree'][1]['content']);return {'sha':'tree'}
            if path=='git/commits':return {'sha':'commit'}
            return {}
        with tempfile.TemporaryDirectory() as root,patch.object(portal,'ROOT',Path(root)),patch.object(portal,'can_manage_bank',return_value=True),patch.object(portal,'read_tex',return_value=(self.path,self.tex)),patch.object(portal,'gh_api',side_effect=github):
            saved=client.post('/api/variable-template/save',json={'src':self.path,'file_idx':self.q['file_idx'],'config':self.c,'confirm_original':True})
            self.assertEqual(saved.status_code,200,saved.text)
            self.assertEqual(vt.load_config(self.q),self.c)
            self.assertIn('def cau_khac', (Path(root)/self.path.rsplit('/',1)[0]/'luyen_tap.py').read_text())
            self.assertEqual(vt.generate_custom(self.q,self.c,True)['answer'],str(-10*sp.sqrt(3)*sp.pi**2))
        with tempfile.TemporaryDirectory() as root,patch.object(dp,'DB_PATH',str(Path(root)/'db.sqlite')),patch.object(portal,'member_current',return_value={'name':'test'}),patch.object(portal,'can_practice',return_value=True),patch.object(portal,'parse_lesson_questions',return_value=[self.q]):
            r=client.post('/api/dynamic-practice/new',json={'path':self.path}).get_json()
            self.assertTrue(r['ok'],r)
            self.assertNotIn('answer',r['exercise']);self.assertNotIn('solution',r['exercise'])
            with client.session_transaction() as sess:owner=sess['dp_owner']
            _,exercise=dp.load_exercise(r['token'],owner)
            idx=next(i for i,o in enumerate(exercise['options']) if o['correct'])
            self.assertTrue(client.post('/api/dynamic-practice/check',json={'token':r['token'],'choice':idx}).get_json()['correct'])
