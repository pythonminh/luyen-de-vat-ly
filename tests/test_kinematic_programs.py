import unittest
from pathlib import Path
import sympy as sp
import app,variable_templates as vt,python_questions as py

class KinematicProgramsTests(unittest.TestCase):
    def question(self,index):
        f=next((app.ROOT/'ngan-hang/Vật lý/Lớp 11/Chương I. Dao động').glob('L11C1 Bài 3.*/de.tex'))
        q=app.parse_questions(f.read_text())[index];q.update(src=str(f.relative_to(app.ROOT)),file_idx=index)
        return q,vt.load_config(q)

    def test_generator_preserves_speed_domain(self):
        q,c=self.question(11)
        self.assertEqual(vt.generate_custom(q,c,True)['answer'],'40')
        for _ in range(30):
            e=vt.generate_custom(q,c);A,w,x=map(sp.Rational,e['params'])
            self.assertLess(abs(x),A)
            self.assertEqual(sp.simplify(sp.sympify(e['answer'])**2+w**2*x**2-w**2*A**2),0)
        q,c=self.question(16)
        for _ in range(30):
            e=vt.generate_custom(q,c);A,w,v=map(sp.Rational,e['params'])
            self.assertLess(v,A*w)
            self.assertEqual(sp.simplify(sp.sympify(e['answer'])**2+(v/w)**2-A**2),0)

    def test_zero_velocity_and_distinct_options(self):
        q,c=self.question(89);e=vt.generate_custom(q,c,True)
        self.assertEqual(e['answer'],'0')
        self.assertEqual(len({o['text'] for o in e['options']}),4)
        self.assertEqual(sum(o['correct'] for o in e['options']),1)

    def test_exact_time_and_original_letter_correction(self):
        q,c=self.question(120);e=vt.generate_custom(q,c,True)
        self.assertEqual(e['answer'],'1/12')
        self.assertTrue(py.same_answer('1/12',e['answer']))
        self.assertFalse(py.same_answer('0.083',e['answer']))
        q,c=self.question(9)
        self.assertEqual(q['answer'],'800')
        self.assertEqual(vt.generate_custom(q,c,True)['answer'],'800')

    def test_mixed_units_and_original_pairs(self):
        q,c=self.question(106);e=vt.generate_custom(q,c,True)
        self.assertEqual(e['answer'],'(10, 1)')
        q,c=self.question(105)
        self.assertEqual(vt.generate_custom(q,c,True)['answer'],'471/50')
        q,c=self.question(91)
        self.assertEqual(vt.generate_custom(q,c,True)['answer'],'9/5')
