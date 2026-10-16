import json
import unittest
from unittest.mock import patch
from test_practice_race import RaceTests
from test_race_variants import questions
import practice_race as race

class Room50Tests(unittest.TestCase):
    setUp = RaceTests.setUp
    tearDown = RaceTests.tearDown
    user_as = RaceTests.user_as
    post = RaceTests.post
    get = RaceTests.get
    start = RaceTests.start

    def test_single_question_mixed_lesson_and_fifty_guests(self):
        qs = [questions()[0], {'kind':'TL','text':'Chứng minh chưa hỗ trợ.'}]
        with patch.object(race.base, 'parse_lesson_questions', return_value=qs):
            preview = self.client.get('/api/race-preview?path=lesson.tex&count=1&mode=numeric')
            self.assertEqual(preview.status_code, 200)
            r = self.client.post('/member/race', data={'csrf':'test-token','path':'lesson.tex','count':'1','minutes':'15','mode':'numeric'})
        self.assertEqual(r.status_code, 302)
        self.code = r.location.rsplit('/', 1)[-1]
        self.user = None
        for i in range(50):
            guest = race.base.app.test_client()
            with guest.session_transaction() as s: s['race_csrf'] = 'test-token'
            r = guest.post('/api/race/'+self.code, json={'action':'join','name':'Học sinh '+str(i+1)}, headers={'X-Race-CSRF':'test-token'})
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        with race.db() as c:
            papers = [json.loads(row[0]) for row in c.execute('SELECT questions FROM race_players WHERE room=?',(self.code,))]
        self.assertEqual(len(papers), 50)
        self.assertEqual(len({race.fingerprint(p[0]) for p in papers}), 50)
        for p in papers:
            q = p[0]
            self.assertTrue(race.correct(q, ';'.join(q['_race_rounded_components']).replace('.', ',')))
            rendered = race.public_question(q)['text']
            self.assertIn('class="race-answer-hint"', rendered)
            self.assertNotIn(race.variants.DECIMAL_HINT, q['text'])
        with self.assertRaises(ValueError): race.numeric_pool(qs, 1, strict=True)

    def test_multiple_result_labels_and_legacy_paper(self):
        q = race.variants.generate(questions()[3], original=True)
        public = race.public_question(q)
        self.assertEqual(public['components'], 2)
        self.assertEqual(public['component_labels'], ['A (độ)', 'S'])
        self.assertNotIn('Nhập theo thứ tự:', public['text'])
        self.assertNotIn('dùng dấu chấm phẩy', public['text'])
        q['text'] += '\n' + race.variants.DECIMAL_HINT
        self.assertEqual(race.public_question(q), public)

    def test_review_shows_own_answer_only_after_close(self):
        self.user_as('alice')
        self.post('join', name='Alice')
        self.start()
        self.user_as('alice')
        before = self.get()
        self.assertNotIn('review', before)
        self.post('submit', answers={'0':0})
        self.assertNotIn('review', self.get())
        self.user_as('teacher')
        self.post('close')
        self.user_as('alice')
        d = self.get()
        item = d['review'][0]
        self.assertTrue(item['answer'].startswith('A. '))
        self.assertIn('expected', item)
        self.assertIn('solution', item)
        q = race.variants.generate(questions()[3], original=True)
        parts = race.student_review(q, ';8,19', False)['parts']
        self.assertEqual(parts[0]['answer'], '(Chưa trả lời)')
        self.assertEqual(parts[1]['answer'], '8,19')
        self.assertEqual(parts[1]['label'], 'S')
        self.assertTrue(parts[0]['expected'])
        self.assertIn('&lt;script&gt;', race.student_review({'kind':'TL','text':'x'}, '<script>', None)['answer'])

    def test_advice_for_wrong_blank_correct_and_pending(self):
        q = race.variants.generate(questions()[3], original=True)
        wrong = race.student_review(q, '1;2', False)
        self.assertTrue(any('arccos' in tip for tip in wrong['advice']))
        self.assertTrue(any('2 chữ số' in tip for tip in wrong['advice']))
        self.assertTrue(any('đủ các ô' in tip for tip in wrong['advice']))
        blank = race.student_review(q, ';', False)
        self.assertIn('chưa trả lời', blank['advice'][0])
        self.assertEqual(race.student_review(q, '1;2', True)['advice'], [])
        self.assertEqual(race.student_review(q, '1;2', None)['advice'], [])
        tn = {'kind':'TN','text':'x','options':[{'text':'1','correct':True}]}
        self.assertNotIn('chưa trả lời', race.student_advice(tn, 0, False)[0])

    def test_closed_room_announces_next_round_and_cannot_join(self):
        self.user_as('alice'); self.post('join', name='Alice')
        self.start(); self.user_as('teacher'); self.post('close')
        first=self.post('new_round').get_json()['redirect']
        second=self.post('new_round').get_json()['redirect']
        self.assertEqual(first,second)
        self.user_as('alice')
        self.assertEqual(self.get()['next_room_url'],first)
        self.assertTrue(self.get()['review'])
        self.user_as('newguest')
        self.assertEqual(self.post('join',name='New Guest').status_code,409)
        self.assertEqual(self.get()['state'],'closed')
        self.assertNotIn('questions',self.get())
        self.code=first.rsplit('/',1)[-1]
        self.assertNotIn('next_room_url',self.get())
        self.assertEqual(self.post('join',name='New Guest').status_code,200)
