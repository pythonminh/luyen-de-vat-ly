import copy
import json
import math
import unittest
from pathlib import Path
from unittest.mock import patch
import sympy as sp
import app
import practice_race as race
import race_set_variants as sets
import race_variants as variants
import test_practice_race as race_tests

QUESTIONS=json.loads((Path(__file__).parent/'fixtures/parameter_sets.json').read_text())

def learner_answer(q):
    ans=q['_race_set_answer']
    if ans['type']=='scalar':return ans['value']
    if ans['type']=='finite':return ';'.join(ans['values']) if ans['values'] else 'rỗng'
    return ' U '.join(('(' if left else '[')+lo.replace('-oo','-inf')+';'+hi.replace('oo','+inf')+(')' if right else ']') for lo,hi,left,right in ans['values'])

class SetVariantTests(unittest.TestCase):
    def test_original_correct_answers_and_boundaries(self):
        answers=['2;3;4','[2;+inf)','2','9','4','0,67','1']
        for q,answer in zip(QUESTIONS,answers):
            item=variants.generate(q,True)
            self.assertTrue(race.correct(item,answer),(q['idx'],answer))
            self.assertFalse(race.correct(item,'999999'))
            self.assertTrue(race.auto_graded(item))
            self.assertNotIn('_race_set_answer',race.public_question(item))
            self.assertTrue(race.expected_label(item))
        q=variants.generate(QUESTIONS[0],True)
        self.assertFalse(variants.matches(q,'1;2;3;4')) # A right-closed; B right-open.
        q=variants.generate(QUESTIONS[1],True)
        self.assertTrue(variants.matches(q,'m>=2'))
        self.assertFalse(variants.matches(q,'(2;+inf)'))
        self.assertFalse(variants.matches(q,'(-inf;-6) U [5;+inf)'))
        _,_,edge,_=sets.solve('empty_intersection',dict(u=1,v=1,k=2,l=0,r=1))
        self.assertEqual(sets.answer_set(edge),sp.Union(sp.FiniteSet(1),sp.Interval(3,sp.oo)))
        self.assertTrue(sets.matches({'_race_set_answer':edge},'[1;1] U [3;+inf)'))
        edited=copy.deepcopy(QUESTIONS[0]);edited['text']=edited['text'].replace('4]','5]')
        self.assertIsNone(sets.spec(edited))

    def test_many_papers_are_distinct_and_auto_graded(self):
        pool,_,capacity=race.numeric_pool(QUESTIONS,7)
        papers=[]
        for _ in range(20):
            paper=race.numeric_allocate(pool,papers)
            for q in paper:
                self.assertTrue(race.correct(q,learner_answer(q)))
                self.assertFalse(race.correct(q,'__import__("os").system("id")'))
                self.assertNotEqual(q['_race_variant_values'],{k:str(v) for k,v in q['_race_variant_spec']['data'].items()})
            papers.append(paper)
        self.assertEqual(capacity,200)
        self.assertEqual(len({race.fingerprint(q) for paper in papers for q in paper}),140)

    def test_answers_against_concrete_interval_operations(self):
        for _ in range(5):
            for source in QUESTIONS:
                q=variants.generate(source)
                kind=q['_race_variant_spec']['type'];p={k:sp.Rational(v) for k,v in q['_race_variant_values'].items()}
                ans=q['_race_set_answer']
                if kind=='positive_subset':
                    found=[]
                    for v in range(1,100):
                        A=sp.Interval(v-p['u'],p['v'],left_open=True);B=sp.Interval(p['l'],p['k']*v+p['t'],left_open=True,right_open=True)
                        if A!=sp.S.EmptySet and B!=sp.S.EmptySet and A.is_subset(B):found.append(str(v))
                    self.assertEqual(ans['values'],found)
                elif kind=='empty_intersection':
                    B=sp.Union(sp.Interval(-sp.oo,p['l'],right_open=True),sp.Interval(p['r'],sp.oo))
                    expected=sets.answer_set(ans)
                    special=[(p['k']*p['u']+p['v'])/(p['k']-1),p['l']+p['u'],p['k']*p['r']-p['v']]
                    probes=[sp.Rational(n,2) for n in range(-20,121)]+[b+d for b in special for d in (-sp.Rational(1,100),0,sp.Rational(1,100))]
                    for v in probes:
                        A=sp.Interval(v-p['u'],(v+p['v'])/p['k'],right_open=True)
                        self.assertEqual(bool(expected.contains(v)),A.intersect(B)==sp.S.EmptySet,(p,v))
                elif kind in ('closed_subset_count','power_set_count','open_subset_count'):
                    found=[]
                    for v in range(-30,101):
                        if kind=='closed_subset_count':A=sp.Interval(v+p['u'],p['k']*v-p['v']);B=sp.Interval(p['l'],p['r'],left_open=True,right_open=True)
                        elif kind=='power_set_count':A=sp.Interval(p['u'],p['v']);B=sp.Interval(p['k']*v+p['p'],p['l']*v+p['q'],left_open=True)
                        else:A=sp.Interval(v,p['k']*v-p['t'],left_open=True,right_open=True);B=sp.Interval(p['u'],p['v'],left_open=True,right_open=True)
                        if A!=sp.S.EmptySet and B!=sp.S.EmptySet and A.is_subset(B):found.append(v)
                    count=2**len(found) if kind=='power_set_count' else len(found)
                    self.assertEqual(int(ans['value']),count,(kind,p))
                elif kind=='singleton_positive':
                    v=sp.Rational(ans['value']);x=p['h']/v
                    self.assertGreater(x,0)
                    self.assertEqual(v*x*x-2*p['h']*x+v-p['t'],0)
                    self.assertEqual(4*p['h']**2-4*v*(v-p['t']),0)
                elif kind=='negative_overlap':
                    self.assertEqual(float(sp.Rational(ans['value'])),round(math.sqrt(float(p['t']/p['k'])),2))

class SetRoomFlowTests(race_tests.RaceTests):
    def test_lesson_dropdown_uses_only_the_named_file(self):
        selected=[{**q,'src':'sets.tex'} for q in QUESTIONS]
        other={'idx':99,'kind':'TL','text':'Câu chưa hỗ trợ từ file khác','src':'other.tex'}
        with patch.object(app,'parse_lesson_questions',return_value=[other]+selected):
            preview=self.client.get('/api/race-preview?path=sets.tex&mode=numeric&count=5').get_json()
            self.assertTrue(preview['ok'],preview)
            self.assertEqual(preview['count'],5)
            self.assertEqual(len(race.source_questions('sets.tex')),7)

    def test_screenshot_lesson_creates_and_grades_each_paper(self):
        with patch.object(app,'parse_lesson_questions',return_value=QUESTIONS):
            preview=self.client.get('/api/race-preview?path=sets.tex&mode=numeric&count=7').get_json()
            self.assertTrue(preview['ok']);self.assertEqual(preview['manual'],0)
            response=self.client.post('/member/race',data={'csrf':'test-token','path':'sets.tex','count':'7','minutes':'15','mode':'numeric'})
        self.assertEqual(response.status_code,302)
        self.code=response.location.rsplit('/',1)[-1]
        for name in ('student1','student2'):
            self.user_as(name);self.assertEqual(self.post('join',name=name).status_code,200)
        self.start();self.user_as('student1')
        with race.db() as c:paper=json.loads(c.execute('SELECT questions FROM race_players WHERE room=? AND user=?',(self.code,'student1')).fetchone()[0])
        response=self.post('submit',answers={str(i):learner_answer(q) for i,q in enumerate(paper)}).get_json()
        self.assertNotIn('results',response)
        self.assertEqual(next(p for p in response['ranking'] if p['me'])['correct'],7)
        self.user_as('teacher');result=self.get()['results'][0]
        self.assertEqual(result['score'],7)
        self.assertTrue(all(q['correct'] is True and q['expected'] for q in result['questions']))
