import base64
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet,InvalidToken
import app
import practice_race as race
import race_archive as archive
import race_variants as variants
import test_practice_race as existing


class HistoryTests(unittest.TestCase):
    setUp=existing.RaceTests.setUp
    tearDown=existing.RaceTests.tearDown
    user_as=existing.RaceTests.user_as
    post=existing.RaceTests.post
    get=existing.RaceTests.get
    start=existing.RaceTests.start

    def fake_remote(self,path,method='GET',payload=None):
        if path.startswith('git/ref/heads/'):
            return {'object':{'sha':'a'*40}}
        if path.startswith('contents/'):
            name=path[len('contents/'):].split('?')[0]
            if method=='GET':
                if name not in self.files:raise RuntimeError('GitHub API 404: Not Found')
                return {'content':base64.b64encode(self.files[name]).decode(),'encoding':'base64','sha':str(self.revision)}
            self.files[name]=base64.b64decode(payload['content']);self.revision+=1
            self.assertEqual(payload['branch'],archive.BRANCH)
            return {'content':{'sha':str(self.revision)}}
        raise AssertionError(path)

    def remote(self):
        self.files={};self.revision=1
        self.enter=patch.dict(os.environ,{'PRACTICE_RACE_ARCHIVE_KEY':Fernet.generate_key().decode()})
        self.enter.start();self.addCleanup(self.enter.stop)
        for p in [patch.object(app,'github_token',return_value='test-token'),patch.object(archive,'api',side_effect=self.fake_remote),patch.object(archive,'enqueue'),patch.object(archive,'_INDEX_CACHE',None),patch.object(archive,'_INDEX_AT',0),patch.object(archive,'_VERIFIED',False)]:
            p.start();self.addCleanup(p.stop)

    def submitted_numeric_room(self):
        q={'idx':0,'kind':'TLN','text':r'Cho tam giác ABC có AB=7, AC=9, A=60. Tính BC.','answer':''}
        with patch.object(app,'parse_lesson_questions',return_value=[q]):
            r=self.client.post('/member/race',data={'csrf':'test-token','path':'triangle.tex','count':'1','minutes':'15','mode':'numeric'})
        self.assertEqual(r.status_code,302);self.code=r.location.rsplit('/',1)[-1]
        self.user_as('student1');self.post('join',name='Học sinh thử nghiệm')
        self.start();self.user_as('student1')
        with race.db() as c:question=json.loads(c.execute('SELECT questions FROM race_players WHERE room=? AND user=?',(self.code,'student1')).fetchone()[0])[0]
        answer=question['_race_rounded_components'][0].replace('.',',')
        self.post('save',answers={'0':'0,00'})
        self.post('save',answers={'0':answer})
        result=self.post('submit',answers={'0':answer}).get_json()
        self.assertEqual(next(p for p in result['ranking'] if p['me'])['correct'],1)
        self.assertNotIn('history_url',result)
        self.user_as('teacher');self.post('close')
        return answer

    def test_archive_restores_full_paper_after_server_replacement(self):
        self.remote();answer=self.submitted_numeric_room()
        self.assertTrue(archive.save(self.code))
        self.assertEqual(archive.status(self.code)['state'],'saved')
        raw=self.files['history/rooms/'+self.code+'.enc']
        self.assertNotIn('Học sinh thử nghiệm'.encode(),raw)
        data=archive.decrypt(raw)
        self.assertTrue(data['race_players'][0]['finished'])
        self.assertEqual(json.loads(data['race_players'][0]['answers'])['0'],answer)
        self.assertTrue(any(e['kind']=='submit' for e in data['race_events']))
        # Simulate a fresh Render filesystem while retaining only the remote files.
        with patch.object(race,'DB_PATH',Path(self.temp.name)/'after-redeploy.sqlite3'):
            listing=self.client.get('/member/race/history')
            self.assertEqual(listing.status_code,200);self.assertIn(self.code,listing.get_data(as_text=True))
            detail=self.client.get('/member/race/history/'+self.code)
            self.assertEqual(detail.status_code,200)
            text=detail.get_data(as_text=True)
            self.assertIn('Học sinh thử nghiệm',text);self.assertIn(answer,text)
            self.assertIn('Kết quả nhập (đã làm tròn)',text)
            self.assertIn('Lịch sử trả lời',text)
            exported=self.client.get('/member/race/history/'+self.code+'/export')
            self.assertEqual(exported.status_code,200)
            self.assertEqual(exported.get_json()['race_players'][0]['answers'],data['race_players'][0]['answers'])
            self.user_as('stranger')
            self.assertEqual(self.client.get('/member/race/history/'+self.code).status_code,403)
            self.assertEqual(self.client.get('/member/race/history/'+self.code+'/export').status_code,403)
            self.user_as('student1')
            mine=self.get();self.assertTrue(mine['review'][0]['correct']);self.assertNotIn('results',mine)

    def test_failed_remote_save_keeps_local_data_and_export(self):
        self.remote();self.submitted_numeric_room()
        with patch.object(archive,'api',side_effect=RuntimeError('offline')):
            self.assertFalse(archive.save(self.code))
            self.assertEqual(archive.status(self.code)['state'],'error')
            r=self.client.get('/member/race/history/'+self.code+'/export')
            self.assertEqual(r.status_code,200)
            self.assertEqual(len(r.get_json()['race_players']),1)
            fail=self.client.post('/member/race/history/'+self.code+'/save',data={'csrf':'test-token'})
            self.assertEqual(fail.status_code,503)

    def test_export_import_preserves_answers_and_timeline(self):
        answer=self.submitted_numeric_room()
        exported=self.client.get('/member/race/history/'+self.code+'/export').data
        with patch.object(race,'DB_PATH',Path(self.temp.name)/'imported.sqlite3'):
            r=self.client.post('/member/race/history/import',data={'csrf':'test-token','backup':(io.BytesIO(exported),'race.json')},content_type='multipart/form-data')
            self.assertEqual(r.status_code,302)
            text=self.client.get(r.location).get_data(as_text=True)
            self.assertIn(answer,text);self.assertIn('Nộp bài',text)
        self.assertEqual(self.client.post('/member/race/history/'+self.code+'/save').status_code,403)

    def test_different_admin_cannot_read_room(self):
        self.submitted_numeric_room();self.user_as('other-admin')
        with patch.object(app,'can_manage_bank',return_value=True):
            self.assertEqual(self.client.get('/member/race/history/'+self.code).status_code,403)
            listing=self.client.get('/member/race/history').get_data(as_text=True)
            self.assertNotIn(self.code,listing)

    def test_encryption_tamper_is_detected(self):
        self.remote();payload={'name':'Private student','answers':{'0':'8,19'}}
        raw=archive.encrypt(payload)
        self.assertEqual(archive.decrypt(raw),payload)
        with patch.dict(os.environ,{'PRACTICE_RACE_ARCHIVE_KEY':Fernet.generate_key().decode()}):
            with self.assertRaises(InvalidToken):archive.decrypt(raw)


class DecimalTests(unittest.TestCase):
    def test_rounding_uses_two_decimals_and_comma(self):
        q={'kind':'TLN','text':'Tính kết quả.','solution':'Lời giải.','_race_answer_components':['sqrt(67)','-1/8','2']}
        q=variants.decimalize(q)
        self.assertEqual(q['_race_rounded_components'],['8.19','-0.13','2'])
        self.assertIn('dấu phẩy (,)',q['text']);self.assertIn('8{,}19',q['_race_answer_display'])
        self.assertTrue(variants.matches(q,'8,19;-0,13;2'))
        self.assertTrue(variants.matches(q,'8.19;-0.13;2'))
        self.assertFalse(variants.matches(q,'8,18;-0,13;2'))
        self.assertFalse(variants.matches(q,'8,19,-0,13,2'))
        self.assertEqual(variants.decimal_value('1.005'),'1.01')
        self.assertEqual(variants.decimal_value('-1.005'),'-1.01')

    def test_triangle_prompt_no_longer_requires_unrounded_expression(self):
        q={'kind':'TLN','text':r'Cho tam giác ABC có AB=7, AC=9, A=60. Tính BC.'}
        q=variants.generate(q,True)
        self.assertIn('làm tròn đến 2',q['text'])
        self.assertNotIn('không tự làm tròn',q['text'])
        self.assertTrue(race.correct(q,'8,19'));self.assertFalse(race.correct(q,'8,18'))


class ArchiveProbeTests(unittest.TestCase):
    def test_probe_starts_in_current_serving_process_after_fork(self):
        from unittest.mock import MagicMock
        old_thread=MagicMock();old_thread.is_alive.return_value=True
        new_thread=MagicMock();new_thread.is_alive.return_value=True
        patches=[patch.object(archive,'configured',return_value=True),patch.object(archive,'_VERIFIED',False),
                 patch.object(archive,'_PROBE_PID',111),patch.object(archive,'_PROBE_AT',10**12),
                 patch.object(archive,'_PROBE_THREAD',old_thread),patch.object(archive.os,'getpid',return_value=222),
                 patch.object(archive.threading,'Thread',return_value=new_thread)]
        for p in patches:p.start();self.addCleanup(p.stop)
        archive.start_probe()
        new_thread.start.assert_called_once()
        self.assertEqual(archive._PROBE_PID,222)
        archive.start_probe()
        new_thread.start.assert_called_once()
