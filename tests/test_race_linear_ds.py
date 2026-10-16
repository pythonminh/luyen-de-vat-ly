import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch
import sympy as sp
from test_practice_race import RaceTests
import practice_race as race
import race_linear_ds as linear
QS=json.loads((Path(__file__).parent/'fixtures/linear_ds.json').read_text())
class LinearTests(unittest.TestCase):
    def test_fifty_private_papers_and_independent_grading(self):
        pool,_,capacity=race.numeric_pool(QS,2)
        self.assertEqual(capacity,200)
        papers=[]
        for _ in range(50):
            paper=race.numeric_allocate(pool,papers);papers.append(paper)
            for q in paper:
                d=q['_race_linear_data']; truths=[o['correct'] for o in q['statements']]
                self.assertTrue(race.correct(q,truths))
                self.assertFalse(race.correct(q,[not t for t in truths]))
                self.assertEqual(race.public_question(q)['kind'],'DS')
                if d['type']=='recognize':
                    expected=[sp.Poly(sp.sympify(f),linear.x,linear.y).total_degree()==1 for f in d['forms']]
                    self.assertEqual(truths,expected)
                else:
                    a,b,c=d['a'],d['b'],d['c'];inside=lambda v:v<=0 if d['lower'] else v>=0
                    for i,(x,y) in enumerate(d['points']):
                        positive='không là' not in q['statements'][i]['text']
                        self.assertEqual(truths[i],inside(a*x+b*y+c)==positive)
                    self.assertEqual(truths[2],all(a*x+b*y+c==0 for x,y in [d['A'],d['B']]))
                    self.assertEqual(truths[3],inside(c)==d['origin_claim'])
        self.assertEqual(len({race.fingerprint(q) for paper in papers for q in paper}),100)
    def test_bank_source_is_recognized_and_corrected(self):
        parsed=race.base.parse_lesson_questions(QS[0]['src'])
        supported=[q for q in parsed if linear.spec(q)]
        self.assertEqual(len(supported),2)
        recognition=next(q for q in supported if linear.spec(q)['type']=='recognize')
        self.assertTrue(recognition['statements'][3]['correct'])

    def test_original_and_unknown(self):
        q=race.variants.generate(QS[1],original=True)
        self.assertEqual([s['correct'] for s in q['statements']],[False,False,True,True])
        q=dict(QS[0],text='Câu khác chưa hỗ trợ')
        self.assertIsNone(linear.spec(q))
class LinearFlowTests(unittest.TestCase):
    setUp=RaceTests.setUp
    tearDown=RaceTests.tearDown
    user_as=RaceTests.user_as
    post=RaceTests.post
    get=RaceTests.get
    start=RaceTests.start
    def test_selected_two_ds_room(self):
        with patch.object(race.base,'parse_lesson_questions',return_value=QS):
            with self.client.session_transaction() as s:s['race_pick']={'token':'picked','path':'lesson.tex','ids':[str(q['idx']) for q in QS]}
            r=self.client.get('/api/race-preview?path=lesson.tex&count=2&mode=numeric&selection=picked')
            self.assertEqual(r.status_code,200,r.get_data(as_text=True))
            r=self.client.post('/member/race',data={'csrf':'test-token','path':'lesson.tex','count':2,'minutes':15,'mode':'numeric','selection':'picked'})
        self.assertEqual(r.status_code,302)
        self.code=r.location.rsplit('/',1)[-1]
        for name in ['alice','bob']:
            self.user_as(name);self.assertEqual(self.post('join',name=name).status_code,200)
        self.start();self.user_as('alice')
        d=self.get();self.assertEqual(len(d['questions']),2);self.assertNotIn('review',d)
        with race.db() as c:q=json.loads(c.execute('SELECT questions FROM race_players WHERE room=? AND user=?',(self.code,'alice')).fetchone()[0])
        d=self.post('submit',answers={str(i):[o['correct'] for o in v['statements']] for i,v in enumerate(q)}).get_json()
        self.assertEqual(next(v for v in d['ranking'] if v['me'])['correct'],2)
