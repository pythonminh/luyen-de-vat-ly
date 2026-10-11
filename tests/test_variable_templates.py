import copy
import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as portal
import dynamic_practice as dp
import variable_templates as vt

class VariableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path='ngan-hang/Vật lý/Lớp 11/Chương I. Dao động/L11C1 Bài 3. Vận tốc, gia tốc trong dao động điều hòa/de.tex'
        cls.qs=portal.parse_questions((portal.ROOT/cls.path).read_text())
        cls.q=next(q for q in cls.qs if q.get('id')=='L11C1B3-31-TN').copy()
        cls.q.update(src=cls.path,file_idx=cls.q['idx'])
        cls.config={'variables':[{'name':'v0','min':'4','max':'12','step':'1'},{'name':'v1','min':'1','max':'6','step':'1'},{'name':'v3','relation':'v0/2'}],'formula':'-v1**2*v3','condition':'v3**2*3 <= v0**2','answer_template':r'${answer}\pi^{2}\sqrt{3}\,\mathrm{cm/s^2}$','solution_template':r'$a={answer}\pi^2\sqrt{3}$','distractors':['-answer','answer*2','answer/2']}

    def test_saved_function_and_1000_variants(self):
        self.assertIsNotNone(self.config)
        original=vt.generate_custom(self.q,self.config,True)
        self.assertEqual(original['answer'],'-10')
        self.assertEqual(original['answer_text'],r'$-10\pi^{2}\sqrt{3}\,\mathrm{cm/s^2}$')
        for _ in range(1000):
            values=vt.saved_function_values(self.q,self.config,False)
            self.assertEqual(values['v3'],values['v0']/2)
            self.assertEqual(values['answer'],-values['v1']**2*values['v3'])
            self.assertLessEqual(values['v3']**2*3,values['v0']**2)
            ex=vt.generate_custom(self.q,self.config)
            self.assertIn(r'\dfrac{\pi}{2}',ex['text'])
            self.assertIn(r'\sqrt{3}',ex['text'])
            self.assertEqual(sum(o['correct'] for o in ex['options']),1)
            self.assertEqual(len({o['text'] for o in ex['options']}),4)
        with patch.object(portal,'read_tex',side_effect=lambda p:(p,(portal.ROOT/p).read_text())):
            lesson=portal.parse_lesson_questions(self.path)
        self.assertTrue(any(g['key']=='custom:'+vt.identity(self.q) for g in dp.groups_for(lesson)))

    def test_exact_slots_and_blocked_code(self):
        self.assertEqual([s['value'] for s in vt.slots(r'12 ngoài $$x=2{,}5$$ và $t=0.2$')],['5/2','1/5'])
        self.assertEqual(vt.evaluate('0.1+0.2',{}),Fraction(3,10))
        for expr in ["__import__('os')",'v0.real','v0[0]','sum([1,2])','2**100']:
            with self.assertRaises(ValueError): vt.evaluate(expr,{'v0':Fraction(2)})
        config=copy.deepcopy(self.config);config['variables'][0]['relation']='v3/2'
        with self.assertRaises(ValueError): vt.source_code(self.q,config)
        with tempfile.TemporaryDirectory() as root,patch.object(portal,'ROOT',Path(root)):
            record=Path(root)/vt.location(self.q);record.parent.mkdir(parents=True)
            record.write_text(json.dumps({'config':self.config}))
            file=Path(root)/self.path.rsplit('/',1)[0]/'luyen_tap.py'
            file.write_text('# BEGIN '+vt.identity(self.q)+'\nimport os\n# END '+vt.identity(self.q))
            with self.assertRaises(ValueError): vt.generate_custom(self.q,self.config)

    def test_admin_preview_and_student_practice(self):
        client=portal.app.test_client()
        with patch.object(portal,'can_manage_bank',return_value=False):
            self.assertEqual(client.get('/api/variable-template').status_code,403)
            self.assertEqual(client.post('/api/variable-template/preview',json={}).status_code,403)
        with tempfile.TemporaryDirectory() as root,patch.object(dp,'DB_PATH',str(Path(root)/'db.sqlite')),patch.object(portal,'can_manage_bank',return_value=True),patch.object(portal,'member_current',return_value={'name':'test'}),patch.object(portal,'can_practice',return_value=True),patch.object(portal,'read_tex',side_effect=lambda p:(p,(portal.ROOT/p).read_text())):
            result=client.post('/api/variable-template/preview',json={'src':self.path,'file_idx':self.q['file_idx'],'config':self.config})
            self.assertEqual(result.status_code,200,result.text)
            self.assertIn('-10',result.get_json()['original']['answer'])
            groups=dp.groups_for(portal.parse_lesson_questions(self.path))
            index=next(i for i,g in enumerate(groups) if g['key']=='custom:'+vt.identity(self.q))
            r=client.post('/api/dynamic-practice/new',json={'path':self.path,'group':index,'source':0}).get_json()
            self.assertTrue(r['ok'],r)
            for field in ['answer','answer_text','solution']:
                self.assertNotIn(field,r['exercise'])
            self.assertTrue(all('correct' not in o for o in r['exercise']['options']))
            with client.session_transaction() as session: owner=session['dp_owner']
            _,stored=dp.load_exercise(r['token'],owner)
            correct=next(i for i,o in enumerate(stored['options']) if o['correct'])
            self.assertTrue(client.post('/api/dynamic-practice/check',json={'token':r['token'],'choice':correct}).get_json()['correct'])
            code=client.get('/api/dynamic-practice/code',query_string={'src':self.path,'file_idx':self.q['file_idx']}).get_json()['code']
            self.assertIn('def '+vt.load_config(self.q)['function_name'],code)

    def test_save_commits_both_files_and_preserves_other_functions(self):
        import base64
        calls=[]
        previous='from fractions import Fraction\nfrom random import randint\n\ndef cau_khac():\n    return 42\n'
        def github(path,method='GET',payload=None):
            calls.append((path,method,payload))
            if path.startswith('git/ref/'): return {'object':{'sha':'parent'}}
            if path=='git/commits/parent': return {'tree':{'sha':'base'}}
            if path.startswith('contents/'): return {'content':base64.b64encode(previous.encode()).decode()}
            if path=='git/trees': return {'sha':'tree'}
            if path=='git/commits': return {'sha':'commit'}
            return {}
        source=(portal.ROOT/self.path).read_text()
        with tempfile.TemporaryDirectory() as root,patch.object(portal,'ROOT',Path(root)),patch.object(portal,'read_tex',return_value=(self.path,source)),patch.object(portal,'can_manage_bank',return_value=True),patch.object(portal,'gh_api',side_effect=github):
            result=portal.app.test_client().post('/api/variable-template/save',json={'src':self.path,'file_idx':self.q['file_idx'],'config':self.config,'confirm_original':True})
            self.assertEqual(result.status_code,200,result.text)
            tree=next(payload for path,method,payload in calls if path=='git/trees')
            self.assertEqual(len(tree['tree']),3)
            self.assertEqual(calls[-1][2],{'sha':'commit','force':False})
            self.assertEqual(vt.load_config(self.q),self.config)
            module=(Path(root)/self.path.rsplit('/',1)[0]/'luyen_tap.py').read_text()
            self.assertIn('def cau_khac():',module)
            self.assertEqual(vt.generate_custom(self.q,self.config,True)['answer'],'-10')
