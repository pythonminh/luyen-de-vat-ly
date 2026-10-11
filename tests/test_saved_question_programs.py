import unittest
from pathlib import Path
import app
import variable_templates as vt
import python_questions as py

class SavedProgramsTests(unittest.TestCase):
    def question(self,lesson,index):
        path=next((app.ROOT/'ngan-hang/Vật lý/Lớp 11/Chương I. Dao động').glob(lesson+'/de.tex'))
        q=app.parse_questions(path.read_text())[index]
        q.update(src=str(path.relative_to(app.ROOT)),file_idx=index)
        return q,vt.load_config(q)

    def test_reversed_time_and_count_in_original(self):
        q,c=self.question('L11C1 Bài 2.*',24)
        self.assertIsNotNone(c)
        ex=vt.generate_custom(q,c,True)
        self.assertEqual(ex['answer'],'1/2')
        self.assertTrue(py.same_answer('0,5',ex['answer']))

    def test_inverse_orbit_and_original_bank_answers(self):
        for index,expected in [(143,'8'),(144,'12'),(145,'16')]:
            q,c=self.question('L11C1 Ôn*',index)
            self.assertEqual(q['answer'],expected)
            self.assertEqual(vt.generate_custom(q,c,True)['answer'],expected)

    def test_pair_answers_and_dependent_time(self):
        q,c=self.question('L11C1 Bài 1.*',5)
        ex=vt.generate_custom(q,c,True)
        self.assertEqual(ex['answer'],'(10, 5)')
        self.assertEqual(sum(o['correct'] for o in ex['options']),1)
        self.assertIn('10',next(o['text'] for o in ex['options'] if o['correct']))
        q,c=self.question('L11C1 Bài 1.*',28)
        for _ in range(30):
            ex=vt.generate_custom(q,c)
            import sympy as sp
            a,w,t=map(sp.Rational,ex['params'])
            self.assertEqual((w*t).q,1)
            self.assertGreater(w*t,0)
            self.assertEqual(sp.Rational(ex['answer']),2*a*w*t)
        standalone=(app.ROOT/vt.location(q)).with_suffix('.py')
        self.assertEqual(vt.verified_source(q,c),standalone.read_text())
