import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import practice_race as race


def bank(n=40):
    return [{'idx': i, 'kind': 'TN', 'text': 'Câu khác nhau ' + str(i), 'dang': 'Dạng 1', 'muc': 'TH',
             'options': [{'text': str(i * 4 + j), 'correct': j == 0} for j in range(4)], 'solution': 'Lời giải'} for i in range(n)]


class RaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(race, 'DB_PATH', Path(self.temp.name) / 'race.sqlite3')
        self.path_patch.start()
        self.user = {'username': 'teacher', 'name': 'Thầy', 'account_type': 'ADMIN'}
        self.patches = [patch.object(app, 'member_current', side_effect=lambda: self.user),
                        patch.object(app, 'can_manage_bank', side_effect=lambda: bool(self.user and self.user['username'] == 'teacher')),
                        patch.object(app, 'can_practice', return_value=True),
                        patch.object(app, 'parse_lesson_questions', return_value=bank())]
        for p in self.patches: p.start()
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()
        with self.client.session_transaction() as s: s['race_csrf'] = 'test-token'
        r = self.client.post('/member/race', data={'csrf': 'test-token', 'path': 'lesson.tex', 'count': '5', 'minutes': '1'})
        self.code = r.location.rsplit('/', 1)[-1]

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def user_as(self, name):
        self.user = {'username': name, 'name': name, 'account_type': 'VIP'}

    def post(self, action, **kwargs):
        return self.client.post('/api/race/' + self.code, json={'action': action, **kwargs}, headers={'X-Race-CSRF': 'test-token'})

    def get(self):
        return self.client.get('/api/race/' + self.code).get_json()

    def start(self):
        self.user_as('teacher')
        return self.post('start')

    def test_disjoint_sets_and_fixed_blueprint(self):
        pool, blueprint, capacity = race.build_pool(bank(), 5)
        self.assertEqual(capacity, 8)
        papers = []
        for _ in range(8): papers.append(race.allocate(pool, blueprint, papers))
        fingerprints = [race.fingerprint(q) for paper in papers for q in paper]
        self.assertEqual(len(set(fingerprints)), 40)
        with self.assertRaises(ValueError): race.allocate(pool, blueprint, papers)
        self.assertEqual([o['text'] for o in pool[0]['options']], ['0','1','2','3'])

    def test_duplicate_copies_cannot_increase_capacity(self):
        qs = bank(5)
        duplicate = copy.deepcopy(qs[0]); duplicate['idx'] = 999; duplicate['options'].reverse()
        pool, _, capacity = race.build_pool(qs + [duplicate], 5)
        self.assertEqual(len(pool), 5)
        self.assertEqual(capacity, 1)

    def test_no_answers_or_questions_before_start_and_resume(self):
        self.user_as('alice'); self.post('join')
        d = self.get(); self.assertNotIn('questions', d)
        self.start(); self.user_as('alice'); d = self.get()
        self.assertEqual(len(d['questions']), 5)
        self.assertNotIn('correct', json.dumps(d['questions']))
        self.assertNotIn('solution', json.dumps(d['questions']))
        self.post('join')
        self.assertEqual(d['questions'], self.get()['questions'])

    def test_host_permissions_and_csrf(self):
        self.user_as('alice')
        self.assertEqual(self.post('start').status_code, 403)
        self.assertEqual(self.post('close').status_code, 403)
        self.assertEqual(self.client.post('/api/race/' + self.code, json={'action':'join'}).status_code, 403)

    def test_student_cannot_access_another_paper(self):
        self.user_as('alice'); self.post('join')
        self.user_as('bob'); self.post('join')
        self.start(); self.user_as('alice'); a = self.get()['questions']
        self.user_as('bob'); b = self.get()['questions']
        self.assertTrue(set(q['text'] for q in a).isdisjoint(q['text'] for q in b))

    def test_server_grades_not_client_claims_and_submission_is_final(self):
        self.user_as('alice'); self.post('join'); self.start(); self.user_as('alice')
        with race.db() as c:
            qs = json.loads(c.execute('SELECT questions FROM race_players WHERE user="alice"').fetchone()[0])
        answers = {str(i): next(j for j,o in enumerate(q['options']) if o['correct']) for i,q in enumerate(qs)}
        d = self.post('submit', answers=answers, correct=0, elapsed=-1000).get_json()
        self.assertEqual(d['ranking'][0]['correct'], 5)
        self.assertGreaterEqual(d['ranking'][0]['elapsed'], 0)
        first = d['ranking'][0]['elapsed']
        self.post('submit', answers={})
        d = self.get(); self.assertEqual(d['ranking'][0]['correct'], 5)
        self.assertEqual(first, d['ranking'][0]['elapsed'])

    def test_deadline_rejects_late_answers_and_auto_finishes(self):
        self.user_as('alice'); self.post('join'); self.start(); self.user_as('alice')
        with race.db() as c: c.execute('UPDATE race_rooms SET started=?', (time.time() - 100,))
        d = self.post('submit', answers={'0': 0}).get_json()
        self.assertEqual(d['state'], 'closed'); self.assertEqual(d['ranking'][0]['elapsed'], 60)
        self.assertEqual(d['answers'], {}); self.assertEqual(d['ranking'][0]['correct'], 0)

    def test_ds_and_short_answer_grading(self):
        q = {'kind': 'DS', 'statements': [{'correct': x} for x in [True,False,True,False]]}
        self.assertTrue(race.correct(q, [True,False,True,False]))
        self.assertFalse(race.correct(q, [1,0,1,0]))
        self.assertTrue(race.correct({'kind':'TLN','answer':'12,5'}, '12.5'))
        self.assertFalse(race.correct({'kind':'TLN','answer':'12'}, '12abc'))

    def test_participant_capacity_enforced(self):
        for i in range(8):
            self.user_as('s' + str(i)); self.assertEqual(self.post('join').status_code, 200)
        self.user_as('extra'); self.assertEqual(self.post('join').status_code, 409)

    def test_join_after_start_refused(self):
        self.user_as('alice'); self.post('join'); self.start(); self.user_as('late')
        self.assertEqual(self.post('join').status_code, 409)

    def test_guest_enters_with_name_without_login_or_vip(self):
        self.user = None
        for url in ('/member/race', '/member/race/', '/race', '/race/', '/member/race/' + self.code, '/member/race/' + self.code + '/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.post('join').status_code, 400)
        with patch.object(app, 'can_practice', return_value=False):
            self.assertEqual(self.post('join', name='Nguyễn Văn An').status_code, 200)
            self.assertEqual(self.post('start').status_code, 403)
            self.assertEqual(self.post('close').status_code, 403)
            self.start(); self.user = None
            d = self.get(); self.assertEqual(len(d['questions']), 5)
            self.assertTrue(d['joined'])
            paper = d['questions']
            self.assertEqual(self.post('save', answers={'0':0}).status_code, 200)
            self.assertEqual(self.get()['answers'], {'0':0})
            self.assertEqual(self.get()['questions'], paper)
            self.assertEqual(self.post('submit', answers={'0':0}).status_code, 200)

    def test_guests_with_same_name_are_separate_players(self):
        self.user = None
        self.client.get('/member/race/' + self.code)
        self.assertEqual(self.post('join', name='An').status_code, 200)
        other = app.app.test_client()
        other.get('/member/race/' + self.code)
        with other.session_transaction() as s: token = s['race_csrf']
        r = other.post('/api/race/' + self.code, json={'action':'join','name':'An'}, headers={'X-Race-CSRF':token})
        self.assertEqual(r.status_code, 200)
        self.assertEqual({p['name'] for p in r.get_json()['ranking']}, {'An','An (2)'})
        self.start(); self.user = None
        mine = self.get()['questions']
        theirs = other.get('/api/race/' + self.code).get_json()['questions']
        self.assertTrue({q['text'] for q in mine}.isdisjoint(q['text'] for q in theirs))

    def test_guest_cannot_create_room(self):
        self.user = None
        r = self.client.post('/member/race', data={'csrf':'test-token','path':'lesson.tex','count':'5','minutes':'1'})
        self.assertEqual(r.status_code, 403)

    def test_admin_creation_is_first_and_preview_checks_capacity(self):
        page = self.client.get('/member/race').get_data(as_text=True)
        self.assertLess(page.index('ADMIN · Tạo phòng'), page.index('Học sinh · Vào phòng'))
        d = self.client.get('/api/race-preview?path=lesson.tex&count=5').get_json()
        self.assertEqual(d['available'], 40)
        self.assertEqual(d['capacity'], 8)
        self.assertEqual(self.client.get('/api/race-preview?path=lesson.tex&count=60').status_code, 400)
        self.user = None
        self.assertEqual(self.client.get('/api/race-preview?path=lesson.tex&count=5').status_code, 403)

    def test_invalid_join_code_has_help_instead_of_raw_404(self):
        self.user = None
        r = self.client.post('/race', data={'code':'1234','csrf':'test-token'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('Mã phòng chưa tồn tại', r.get_data(as_text=True))
        r = self.client.get('/member/race/1234')
        self.assertEqual(r.status_code, 404)
        self.assertIn('Tạo phòng / Nhập mã khác', r.get_data(as_text=True))

    def test_qr_encodes_room_join_url_and_guest_can_fetch_it(self):
        page = self.client.get('/member/race/' + self.code).get_data(as_text=True)
        self.assertIn('/race/' + self.code + '/qr.svg', page)
        self.user = None
        real = race.segno.make
        with patch.object(race.segno, 'make', wraps=real) as encoder:
            r = self.client.get('/race/' + self.code + '/qr.svg')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/svg+xml')
            self.assertIn(b'<svg', r.data)
            self.assertTrue(encoder.call_args.args[0].endswith('/member/race/' + self.code))

    def test_selected_questions_flow_uses_only_checked_questions(self):
        r = self.client.post('/member/race/from-selected', data={'race_pick_csrf':'test-token','path':'lesson.tex','qid':['0','1','2','3','4','5','6','7','8','9']})
        self.assertEqual(r.status_code, 302)
        token = r.location.split('selection=')[1]
        page = self.client.get(r.location).get_data(as_text=True)
        self.assertIn('Đã chọn 10 câu', page)
        self.assertIn('name="selection" value="' + token + '"', page)
        d = self.client.get('/api/race-preview?path=lesson.tex&count=5&selection=' + token).get_json()
        self.assertEqual(d['available'], 10)
        self.assertEqual(d['capacity'], 2)
        r = self.client.post('/member/race', data={'csrf':'test-token','path':'lesson.tex','selection':token,'count':'5','minutes':'1'})
        self.assertEqual(r.status_code, 302)
        code = r.location.rsplit('/',1)[-1]
        with race.db() as c:
            pool = json.loads(c.execute('SELECT pool FROM race_rooms WHERE code=?',(code,)).fetchone()[0])
        self.assertEqual({q['idx'] for q in pool}, set(range(10)))

    def test_selected_questions_reject_tampering_and_guests(self):
        r = self.client.post('/member/race/from-selected', data={'race_pick_csrf':'test-token','path':'lesson.tex','qid':['99999']})
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/member/race/from-selected', data={'path':'lesson.tex','qid':['0']})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get('/api/race-preview?path=lesson.tex&count=1&selection=forged').status_code, 400)
        self.user = None
        self.assertEqual(self.client.post('/member/race/from-selected', data={'race_pick_csrf':'test-token','path':'lesson.tex','qid':['0']}).status_code, 403)

    def test_blank_answer_and_essay_room_can_run_then_admin_grades(self):
        manual = [{'idx':0,'kind':'TLN','text':'Tính BC.','answer':'','solution':'BC = √67.'},
                  {'idx':1,'kind':'TL','text':'Giải tam giác ABC.','solution':'Lời giải mẫu.'}]
        with patch.object(app, 'parse_lesson_questions', return_value=manual):
            r = self.client.post('/member/race/from-selected', data={'race_pick_csrf':'test-token','path':'lesson.tex','qid':['0','1']})
            self.assertEqual(r.status_code, 302)
            token = r.location.split('selection=')[1]
            page = self.client.get(r.location).get_data(as_text=True)
            self.assertIn('2 câu cần ADMIN chấm nếu dùng chế độ ngân hàng', page)
            r = self.client.post('/member/race', data={'csrf':'test-token','path':'lesson.tex','selection':token,'count':'1','minutes':'1'})
            self.code = r.location.rsplit('/',1)[-1]
        self.user_as('alice'); self.assertEqual(self.post('join').status_code,200)
        self.start(); self.user_as('alice')
        self.assertTrue(self.get()['questions'][0]['manual'])
        d = self.post('submit', answers={'0':'Bài làm tự luận của em.'}).get_json()
        self.assertFalse(d['ranking'][0]['done'])
        self.assertEqual(d['ranking'][0]['pending'],1)
        self.assertNotIn('grading',d)
        self.assertEqual(self.post('grade',player='alice',pos=0,correct=True).status_code,403)
        self.user_as('teacher')
        d = self.get();self.assertEqual(len(d['grading']),1)
        self.assertEqual(d['grading'][0]['answer'],'Bài làm tự luận của em.')
        elapsed = d['ranking'][0]['elapsed']
        d = self.post('grade',player='alice',pos=0,correct=True).get_json()
        self.assertEqual(d['ranking'][0]['correct'],1)
        self.assertTrue(d['ranking'][0]['done'])
        self.assertEqual(d['ranking'][0]['elapsed'],elapsed)
        d = self.post('grade',player='alice',pos=0,correct=False).get_json()
        self.assertEqual(d['ranking'][0]['correct'],0)

    def test_blank_answer_is_not_guessed_from_solution(self):
        q={'kind':'TLN','text':'Tính cạnh','answer':'','solution':'BC=√67'}
        self.assertTrue(race.eligible(q))
        self.assertFalse(race.auto_graded(q))
        self.assertFalse(race.correct(q,'√67'))


if __name__ == '__main__': unittest.main()
