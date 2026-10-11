import base64
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as portal
import dynamic_practice as dp
from dynamic_engine import exact, fraction, generate, solve

class EngineTests(unittest.TestCase):
    def test_original_results_and_7000_variants(self):
        cases={'acceleration':(['6','4','4'],'96'),'amplitude':(['12'],'6'),'projection':(['10','5'],'10;5'),'period':(['1','30'],'2'),'orbit':(['10','120'],'6'),'distance':(['2.5','4','6','3.75'],'75'),'rotation':(['15','2'],'1;1'),'spring':(['25','12.5','0.08'],'12,8')}
        for key,(p,answer) in cases.items():
            self.assertEqual(solve(key,p)['answer'],answer)
            for _ in range(1000):
                next_params=generate(key,previous=p)
                self.assertNotEqual(list(map(fraction,p)),list(map(fraction,next_params)))
                exercise=solve(key,next_params)
                self.assertEqual(len(exercise['options']),4)
                self.assertEqual(sum(o['correct'] for o in exercise['options']),1)
                self.assertEqual(len({o['text'] for o in exercise['options']}),4)
        self.assertEqual(exact(fraction('1/3')),'1/3')
        self.assertEqual(exact(fraction('64/5')),'12,8')

    def test_distances_against_turning_points(self):
        for denom in [3,4,6]:
            for half_periods in [1,3,15,21]:
                phase=math.pi/denom
                end=phase+half_periods*math.pi
                angles=[phase]+[k*math.pi for k in range(1,half_periods+1) if k*math.pi<end]+[end]
                distance=sum(abs(3*math.cos(b)-3*math.cos(a)) for a,b in zip(angles,angles[1:]))
                result=solve('distance',['3','5',str(denom),str(fraction(half_periods)/5)])
                self.assertAlmostEqual(distance,float(fraction(result['answer'])),places=10)
        with self.assertRaises(ValueError): solve('distance',['3','5','3','4.1'])

    def test_config_validation(self):
        self.assertEqual(generate('amplitude',{'A':{'min':7,'max':7}}),['14'])
        for bounds in [{'A':{'min':0,'max':10}},{'A':{'min':8,'max':2}},{'A':{'min':1.5,'max':2}},{'code':'import os'}]:
            with self.assertRaises(ValueError): generate('amplitude',bounds)

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path='ngan-hang/Vật lý/Lớp 11/Chương I. Dao động/L11C1 Bài 1. Dao động điều hòa/de.tex'
        cls.qs=portal.parse_questions((Path(portal.__file__).parent/cls.path).read_text())

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dbpatch=patch.object(dp,'DB_PATH',str(Path(self.tmp.name)/'exercises.sqlite3'))
        self.dbpatch.start();self.addCleanup(self.dbpatch.stop)
        for name,value in [('member_current',{'name':'test'}),('can_practice',True),('can_manage_bank',True)]:
            p=patch.object(portal,name,return_value=value);p.start();self.addCleanup(p.stop)
        p=patch.object(portal,'parse_lesson_questions',return_value=self.qs);p.start();self.addCleanup(p.stop)
        self.client=portal.app.test_client()

    def new(self,**kwargs):
        return self.client.post('/api/dynamic-practice/new',json={'path':self.path,'group':0,'source':0,**kwargs})

    def test_groups_and_page_without_answers(self):
        before=json.dumps(self.qs,ensure_ascii=False)
        groups=dp.groups_for(self.qs)
        self.assertEqual(len(groups),7)
        self.assertEqual(sum(len(g['items']) for g in groups),8)
        self.assertEqual(json.dumps(self.qs,ensure_ascii=False),before)
        with patch.object(portal,'page',side_effect=lambda title,body:body):
            response=self.client.get('/member/dynamic-practice',query_string={'path':self.path})
        import re
        packed=re.search(r'id="dpData" type="application/json">(.*?)</script>',response.text).group(1)
        data=json.loads(base64.b64decode(packed))
        self.assertNotIn('original',json.dumps(data))
        self.assertNotIn('answer',json.dumps(data))
        self.assertIn('dpConfig',response.text)

    def test_exact_answer_solution_and_no_leaks(self):
        # First group is spring, source is TLN; preserve type and original answer.
        r=self.new(original=True).get_json()
        self.assertTrue(r['ok']);self.assertFalse(r['exercise']['options'])
        for field in ('answer','solution','correct'):
            self.assertNotIn(field,json.dumps(r))
        self.assertTrue(self.client.post('/api/dynamic-practice/check',json={'token':r['token'],'answer':'64/5'}).get_json()['correct'])
        self.assertFalse(self.client.post('/api/dynamic-practice/check',json={'token':r['token'],'answer':'13'}).get_json()['correct'])
        solution=self.client.post('/api/dynamic-practice/solution',json={'token':r['token']}).get_json()
        self.assertIn('12{,}8',solution['solution'])
        other=portal.app.test_client()
        self.assertEqual(other.post('/api/dynamic-practice/solution',json={'token':r['token']}).status_code,403)
        # Known preset => k = 40 * 0.08 / (0.5)^2 = 12.8.
        bounds={n:{'min':v,'max':v} for n,v in [('N',25),('tenths',5),('grams',80)]}
        r=self.new(bounds=bounds).get_json()
        self.assertTrue(self.client.post('/api/dynamic-practice/check',json={'token':r['token'],'answer':'12,8'}).get_json()['correct'])

    def test_admin_code_and_acceleration(self):
        r=self.client.get('/api/dynamic-practice/code')
        self.assertEqual(r.status_code,200)
        self.assertIn('def generate',r.get_json()['code'])
        with patch.object(portal,'can_manage_bank',return_value=False):
            self.assertEqual(self.client.get('/api/dynamic-practice/code').status_code,403)
        spec=dp.classify({'kind':'TN','text':r'Một vật có $x=6\cos(4\pi t+\frac{\pi}{4})$ cm. Tìm gia tốc cực đại.'})
        self.assertEqual(spec['template'],'acceleration')
        exercise=solve(spec['template'],spec['params'])
        self.assertIn('96π²',exercise['solution'])
        self.assertTrue(any(o['correct'] and o['text']=='96 π² cm/s²' for o in exercise['options']))

    def test_access_and_bad_inputs(self):
        with patch.object(portal,'member_current',return_value=None): self.assertEqual(self.new().status_code,401)
        with patch.object(portal,'can_practice',return_value=False): self.assertEqual(self.new().status_code,403)
        with patch.object(portal,'can_manage_bank',return_value=False): self.assertEqual(self.new(bounds={'N':{'min':1,'max':2}}).status_code,403)
        self.assertEqual(self.new(group=-1).status_code,400)
        self.assertEqual(self.new(bounds={'N':{'min':0,'max':4}}).status_code,400)
        self.assertEqual(self.client.post('/api/dynamic-practice/check',json={'token':'unknown'}).status_code,403)

if __name__=='__main__': unittest.main()
