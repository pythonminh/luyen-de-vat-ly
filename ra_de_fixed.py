# Compatibility shim: wsgi.py imports ra_de_fixed.
# The active implementation is ra_de.py.
import io

import ra_de

# Patch parser / question writer so LaTeX formulas become native Word OMML equations.
try:
    from word_math import patch_module, add_mixed_latex
    patch_module(ra_de.__dict__)

    # ra_de.py calls _build_word_file() directly. Override that function so the
    # patched OMML question writer is actually used when exporting .docx.
    def _build_word_file(content, ten_de):
        Document = ra_de.Document
        Cm = ra_de.Cm
        Pt = ra_de.Pt
        WD_ALIGN_PARAGRAPH = ra_de.WD_ALIGN_PARAGRAPH

        doc = Document()
        sec = doc.sections[0]
        sec.top_margin = Cm(1.6)
        sec.bottom_margin = Cm(1.6)
        sec.left_margin = Cm(1.8)
        sec.right_margin = Cm(1.8)

        doc.styles["Normal"].font.name = "Arial"
        doc.styles["Normal"].font.size = Pt(11)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(ten_de or "Đề ôn tập")
        r.bold = True
        r.font.size = Pt(16)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = p.add_run("Đề được tạo tự động từ ngân hàng câu hỏi GitHub")
        rr.italic = True

        grouped = ra_de._blocks_from_generated(content)
        sections = [
            ("A", "PHẦN A. TRẮC NGHIỆM 4 LỰA CHỌN"),
            ("B", "PHẦN B. TRẮC NGHIỆM ĐÚNG / SAI"),
            ("C", "PHẦN C. TRẢ LỜI NGẮN"),
            ("D", "PHẦN D. TỰ LUẬN"),
        ]

        for code, heading in sections:
            blocks = grouped.get(code, [])
            if not blocks:
                continue

            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(10)
            hr = h.add_run(heading)
            hr.bold = True
            hr.font.size = Pt(13)

            for i, block in enumerate(blocks, 1):
                # word_math.patch_module() has replaced _add_docx_question
                # with an implementation that writes $...$ as native OMML.
                ra_de._add_docx_question(doc, i, block, code)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    ra_de._build_word_file = _build_word_file

except Exception as _word_math_error:
    # Keep /ra-de usable even if the optional math patch fails.
    ra_de._WORD_MATH_PATCH_ERROR = str(_word_math_error)

bp = ra_de.bp

__all__ = ["bp"]
