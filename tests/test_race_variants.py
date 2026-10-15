import json
import unittest
from unittest.mock import patch

import sympy as sp
import race_variants as variants
import practice_race as race
from test_practice_race import RaceTests

STEMS = [
    r'Cho tam giác \(ABC\) có \(AB=7\), \(AC=9\), \(\widehat{A}=60^\circ\). Tính độ dài cạnh \(BC\).',
    r'Cho tam giác ABC có AB=10, AC=6, BC=8. Tính góc A.',
    r'Cho tam giác ABC có BC=12, A=30, B=45. Tính cạnh CA.',
    r'Cho tam giác ABC có AB=5, AC=7, BC=9. Tính A và diện tích tam giác.',
    r'Cho tam giác ABC có AB=8, AC=10, A=120. Tính BC và bán kính đường tròn ngoại tiếp R.',
    r'(định lý sin) Cho a=8, b=10, A=30. Hỏi có bao nhiêu tam giác? Tính các góc.',
    r'Giải tam giác ABC, biết c=14, A=60, B=40.'
]

def questions():
    return [{'idx':i,'kind':'TLN','text':t,'solution':'','answer':''} for i,t in enumerate(STEMS)]

def answer(q):
    return ';'.join(str(variants.parse_expression(v, False).evalf(15)) for v in q['_race_answer_components'])

class VariantTests(unittest.TestCase):
    def test_seven_solvers_and_disjoint_numbers(self):
        pool,_,capacity = race.numeric_pool(questions(), 7)
        self.assertEqual(capacity,200)
        papers=[]
        for _ in range(10):
            paper=race.numeric_allocate(pool,papers)
            for q in paper:
                self.assertTrue(race.auto_graded(q))
                self.assertTrue(race.correct(q,answer(q)))
                self.assertFalse(race.correct(q,'99999'))
                self.assertNotIn('_race_answer_components',race.public_question(q))
            papers.append(paper)
        self.assertEqual(len({race.fingerprint(q) for paper in papers for q in paper}),70)

    def test_original_exact_answers(self):
        qs=[variants.generate(q,True) for q in questions()]
        self.assertTrue(variants.matches(qs[0],'sqrt(67)'))
        self.assertTrue(variants.matches(qs[1],'acos(3/5)'))
        self.assertTrue(variants.matches(qs[2],'12*sqrt(2)'))
        self.assertTrue(variants.matches(qs[3],'acos(-1/10);21*sqrt(11)/4'))
        self.assertTrue(variants.matches(qs[4],'2*sqrt(61);2*sqrt(183)/3'))
        self.assertTrue(variants.matches(qs[5],'2;asin(5/8);150-asin(5/8);180-asin(5/8);asin(5/8)-30'))
        self.assertTrue(variants.matches(qs[6],'80;14*sin(60)/sin(80);14*sin(40)/sin(80)'))

    def test_reject_unsupported_and_invalid_expressions(self):
        with self.assertRaises(ValueError):race.numeric_pool([{'kind':'TL','text':'Chứng minh tam giác ABC cân.'}],1)
        q=variants.generate(questions()[0],True)
        for a in ['__import__("os").system("id")','sqrt(-1)','1/0','9**999999','[1][0]','nan','1e-999999999']:
            self.assertFalse(variants.matches(q,a))

class NumericFlowTests(RaceTests):
    def test_numeric_room_flow_and_new_round(self):
        with patch.object(race.base,'parse_lesson_questions',return_value=questions()):
            r=self.client.post('/member/race',data={'csrf':'test-token','path':'lesson.tex','count':'7','minutes':'1','mode':'numeric'})
        self.assertEqual(r.status_code,302)
        self.code=r.location.rsplit('/',1)[-1]
        before=self.get()['reference']
        changed=self.post('variant').get_json()['reference']
        self.assertNotEqual(before,changed)
        for name in ['student1','student2','student3']:
            self.user_as(name)
            self.assertEqual(self.post('join',name=name).status_code,200)
            self.assertNotIn('questions',self.get())
            self.assertEqual(self.post('variant').status_code,403)
        self.start()
        self.user_as('student1')
        with race.db() as c:
            row=c.execute('SELECT questions FROM race_players WHERE room=? AND user=?',(self.code,'student1')).fetchone()
            paper=json.loads(row[0])
        d=self.post('submit',answers={str(i):answer(q) for i,q in enumerate(paper)}).get_json()
        ranked=next(p for p in d['ranking'] if p['me'])
        self.assertTrue(ranked['done']);self.assertEqual(ranked['correct'],7)
        self.user_as('teacher')
        self.post('close')
        d=self.post('new_round').get_json()
        self.assertTrue(d['redirect'].startswith('/member/race/'))
        new=self.client.get('/api/race/'+d['redirect'].rsplit('/',1)[1]).get_json()
        self.assertEqual(new['state'],'waiting');self.assertEqual(new['ranking'],[])
        self.assertEqual(self.get()['state'],'closed')
