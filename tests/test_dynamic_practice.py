import base64
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as portal
from dynamic_practice import classify, groups_for

class DynamicPracticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = 'ngan-hang/Vật lý/Lớp 11/Chương I. Dao động/L11C1 Bài 1. Dao động điều hòa/de.tex'
        cls.qs = portal.parse_questions((Path(portal.__file__).parent / cls.path).read_text())

    def test_verified_templates_and_unchanged_bank(self):
        before = json.dumps(self.qs, ensure_ascii=False)
        groups = groups_for(self.qs)
        self.assertEqual(len(groups), 7)
        self.assertEqual(sum(len(g['items']) for g in groups), 8)
        self.assertEqual(len(next(g for g in groups if g['key'] == 'period')['items']), 2)
        self.assertEqual(json.dumps(self.qs, ensure_ascii=False), before)
        self.assertIsNone(classify({'kind': 'TN', 'text': 'Một câu chưa có mô hình 12.'}))
        self.assertIsNone(classify({'kind': 'DS', 'text': self.qs[4]['text']}))

    def test_guest_redirect_and_denied_member(self):
        client=portal.app.test_client()
        with patch.object(portal, 'member_current', return_value=None):
            self.assertEqual(client.get('/member/dynamic-practice', query_string={'path':self.path}).status_code,302)
        with patch.object(portal, 'member_current', return_value={'name':'test'}), patch.object(portal, 'can_practice', return_value=False), patch.object(portal, 'parse_lesson_questions') as parse:
            self.assertEqual(client.get('/member/dynamic-practice', query_string={'path':self.path}).status_code,302)
            parse.assert_not_called()

    def test_authorized_page_keeps_original_data(self):
        with patch.object(portal, 'member_current', return_value={'name':'test'}), patch.object(portal, 'can_practice', return_value=True), patch.object(portal, 'parse_lesson_questions', return_value=self.qs), patch.object(portal, 'page', side_effect=lambda title,body:body):
            response=portal.app.test_client().get('/member/dynamic-practice', query_string={'path':self.path})
        self.assertEqual(response.status_code,200)
        import re
        packed=re.search(r'id="dpData" type="application/json">(.*?)</script>',response.text).group(1)
        groups=json.loads(base64.b64decode(packed))
        spring=next(g for g in groups if g['key']=='spring')['items'][0]
        self.assertEqual(spring['original']['answer'],'12,8')
        self.assertIn('dynamic-practice.js',response.text)

if __name__=='__main__': unittest.main()
