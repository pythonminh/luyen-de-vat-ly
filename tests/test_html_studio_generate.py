# -*- coding: utf-8 -*-
import io
import unittest
import zipfile
from unittest.mock import patch

import app
import html_studio_generate as studio


class HtmlStudioGenerateTests(unittest.TestCase):
    def test_offline_html_validation(self):
        original = '<!doctype html><html><head></head><body><button>Đổi đề</button><script>let x=2;</script></body></html>'
        self.assertEqual(studio._clean_html(original), original)
        self.assertEqual(studio._clean_html('Here is the code:\n'+original), original)
        for bad in [
            '<html><body>no script</body></html>',
            '<html><script src="https://example.com/a.js"></script></html>',
            '<html><script>fetch("https://evil.example")</script></html>',
            '<html><iframe src="other"></iframe><script></script></html>',
        ]:
            with self.assertRaises(ValueError):
                studio._clean_html(bad)

    def test_image_mime_is_verified_from_file_content(self):
        self.assertEqual(studio._image_mime(b'\xff\xd8\xff\xe0hello'), 'image/jpeg')
        self.assertEqual(studio._image_mime(b'\x89PNG\r\n\x1a\nrest'), 'image/png')
        self.assertEqual(studio._image_mime(b'RIFF1234WEBPdata'), 'image/webp')
        self.assertEqual(studio._image_mime(b'<script>bad</script>'), '')

    def test_docx_extracts_paragraphs(self):
        buf=io.BytesIO()
        xml=b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Gia toc 5 m/s2</w:t></w:r></w:p></w:body></w:document>'
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('word/document.xml', xml)
        text,images=studio._docx_parts(buf.getvalue())
        self.assertIn('Gia toc',text)
        self.assertEqual(images,[])

    def test_route_is_admin_only_and_csrf_protected(self):
        client=app.app.test_client()
        with patch.object(studio,'can_manage_bank',return_value=False):
            response=client.post('/admin/html-studio/generate')
            self.assertEqual(response.status_code,403)
        with patch.object(studio,'can_manage_bank',return_value=True):
            response=client.post('/admin/html-studio/generate')
            self.assertEqual(response.status_code,403)

    def test_draft_returns_preview_without_saving(self):
        valid = '<!doctype html><html><head><style>body{color:black}</style></head><body><button onclick="n++">Đổi đề</button><script>let n=0;</script></body></html>'
        client=app.app.test_client()
        with client.session_transaction() as sess:
            sess['html_practice_csrf']='test123'
        with patch.object(studio,'can_manage_bank',return_value=True), \
             patch.object(studio,'_checked_context',return_value=({'mon':'Vật lý','lop':'10','bai':'Chuyển động'},[])), \
             patch('student_gemini._gemini_generate',return_value=valid) as ai, \
             patch.object(app,'github_put_text',side_effect=AssertionError('Must not save before review')):
            response=client.post('/admin/html-studio/generate',data={
                'csrf':'test123','path':'ngan-hang/Vật lý/Lớp 10/Chuyển động/de.tex',
                'api_key':'key_'+'x'*30,'text':'Tính v=s/t, s=20 m, t=4 s.',
                'instruction':'Mẫu ba câu','dang':'',
            })
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(response.get_json()['source'],valid)
        self.assertTrue(ai.called)
        self.assertNotIn('key_'+('x'*30),response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
