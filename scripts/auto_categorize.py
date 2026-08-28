#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tự động phân dạng bài tập - Tạo mục lục phân loại cho tất cả bài học
Auto-categorizes questions and generates organized index for all lessons
"""

import re
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional

class QuestionCategorizer:
    """Phân dạng bài tập theo từng bài học"""
    
    QUESTION_TYPES = {
        'DS': 'Đúng/Sai',
        'TN': 'Trắc nghiệm',
        'TL': 'Tự luận',
        'TLN': 'Tự luận ngắn'
    }
    
    DIFFICULTY_LEVELS = {
        'NB': 'Nhận biết',
        'TH': 'Thông hiểu',
        'VD': 'Vận dụng',
        'VDC': 'Vận dụng cao'
    }
    
    def __init__(self):
        self.lessons = defaultdict(lambda: {
            'file': '',
            'metadata': {},
            'questions': defaultdict(list),  # Phân loại theo dạng
            'stats': {}
        })
    
    def parse_tex_file(self, filepath: str) -> tuple:
        """Phân tích file TeX"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Lỗi đọc file: {e}")
            return None, []
        
        # Trích xuất metadata từ comment đầu file
        metadata = self._extract_metadata(content)
        
        # Trích xuất các câu hỏi
        questions = self._extract_questions(content)
        
        return metadata, questions
    
    def _extract_metadata(self, content: str) -> Dict:
        """Trích xuất thông tin môn/lớp/chương/bài từ file"""
        metadata = {
            'mon': '',
            'lop': '',
            'chuong': '',
            'bai': '',
            'so_cau': 0
        }
        
        lines = content.split('\n')[:15]
        for line in lines:
            if '% Môn:' in line:
                metadata['mon'] = line.split('% Môn:')[1].strip()
            elif '% Lớp:' in line:
                metadata['lop'] = line.split('% Lớp:')[1].strip()
            elif '% Chương:' in line:
                metadata['chuong'] = line.split('% Chương:')[1].strip()
            elif '% Bài:' in line:
                metadata['bai'] = line.split('% Bài:')[1].strip()
            elif '% Số câu:' in line:
                try:
                    metadata['so_cau'] = int(line.split('% Số câu:')[1].strip())
                except:
                    pass
        
        return metadata
    
    def _extract_questions(self, content: str) -> List[Dict]:
        """Trích xuất tất cả câu hỏi"""
        questions = []
        
        # Chia thành các khối câu hỏi
        blocks = re.split(r'%\s*=====\s*Câu\s+(\d+)\s*=====', content)
        
        for i in range(1, len(blocks), 2):
            if i + 1 < len(blocks):
                cau_num = blocks[i]
                cau_block = blocks[i + 1]
                
                q = self._parse_question_block(cau_block, int(cau_num))
                if q:
                    questions.append(q)
        
        return questions
    
    def _parse_question_block(self, block: str, cau_num: int) -> Optional[Dict]:
        """Phân tích một khối câu hỏi"""
        # Trích xuất ID
        id_match = re.search(r'%\s*ID:\s*([A-Za-z0-9\-]+)', block)
        if not id_match:
            return None
        
        qid = id_match.group(1)
        
        # Xác định loại câu
        qtype = None
        for t in ['TLN', 'TL', 'DS', 'TN']:
            if qid.endswith('-' + t):
                qtype = t
                break
        
        if not qtype:
            return None
        
        # Trích xuất mức độ
        level_match = re.search(r'%\s*Mức:\s*([A-Za-z0-9]+)', block)
        level = level_match.group(1) if level_match else 'Unknown'
        
        # Trích xuất dạng bài
        dangbt_match = re.search(r'\\dangbt\{([^}]+)\}', block)
        question_desc = dangbt_match.group(1) if dangbt_match else "Không xác định"
        
        # Trích xuất nội dung câu hỏi (100 ký tự đầu)
        question_text_match = re.search(r'\\begin\{ex\}(.*?)(\\choice|\\choiceTF|\\shortans|\\end\{ex\})', block, re.DOTALL)
        question_text = ""
        if question_text_match:
            question_text = question_text_match.group(1).strip()
            # Xóa các lệnh LaTeX
            question_text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', question_text)
            question_text = re.sub(r'\\[a-zA-Z]+', '', question_text)
            question_text = question_text[:80].strip()
        
        return {
            'so_thu_tu': cau_num,
            'id': qid,
            'type': qtype,
            'type_name': self.QUESTION_TYPES.get(qtype, '?'),
            'level': level,
            'level_name': self.DIFFICULTY_LEVELS.get(level, '?'),
            'description': question_desc,
            'text': question_text
        }
    
    def classify_file(self, filepath: str):
        """Phân loại file"""
        print(f"📄 Xử lý: {Path(filepath).name}")
        
        metadata, questions = self.parse_tex_file(filepath)
        
        if not metadata or metadata['bai'] == '':
            print(f"⚠️  Không tìm thấy thông tin bài học")
            return
        
        lesson_key = metadata['bai']
        
        # Phân loại câu hỏi theo dạng
        grouped_questions = defaultdict(list)
        for q in questions:
            dang_key = f"{q['type']}-{q['level']}"
            grouped_questions[dang_key].append(q)
        
        # Lưu vào lessons
        self.lessons[lesson_key]['file'] = str(filepath)
        self.lessons[lesson_key]['metadata'] = metadata
        self.lessons[lesson_key]['questions'] = dict(grouped_questions)
        self.lessons[lesson_key]['stats'] = self._calculate_stats(questions)
        
        print(f"✅ {metadata['bai']}: {len(questions)} câu")
    
    def _calculate_stats(self, questions: List[Dict]) -> Dict:
        """Tính thống kê"""
        stats = {
            'total': len(questions),
            'by_type': defaultdict(int),
            'by_level': defaultdict(int),
            'by_category': defaultdict(int)
        }
        
        for q in questions:
            stats['by_type'][q['type']] += 1
            stats['by_level'][q['level']] += 1
            cat = f"{q['type']}-{q['level']}"
            stats['by_category'][cat] += 1
        
        return {k: dict(v) if isinstance(v, defaultdict) else v 
                for k, v in stats.items()}
    
    def generate_index_json(self, output_dir: str = 'output'):
        """Tạo mục lục JSON tổng hợp"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Tổng hợp thông tin
        index_data = {
            'tong_bai': len(self.lessons),
            'tong_cau': sum(ls['stats']['total'] for ls in self.lessons.values()),
            'lessons': {}
        }
        
        for lesson_key in sorted(self.lessons.keys()):
            lesson = self.lessons[lesson_key]
            
            # Nhóm câu theo dạng
            dang_groups = {}
            for dang_key, questions in lesson['questions'].items():
                qtype, level = dang_key.split('-')
                if qtype not in dang_groups:
                    dang_groups[qtype] = {'name': self.QUESTION_TYPES[qtype], 'groups': {}}
                
                if level not in dang_groups[qtype]['groups']:
                    dang_groups[qtype]['groups'][level] = {
                        'level_name': self.DIFFICULTY_LEVELS[level],
                        'count': 0,
                        'questions': []
                    }
                
                dang_groups[qtype]['groups'][level]['count'] = len(questions)
                dang_groups[qtype]['groups'][level]['questions'] = [
                    {
                        'id': q['id'],
                        'so_thu_tu': q['so_thu_tu'],
                        'text': q['text']
                    } for q in questions
                ]
            
            index_data['lessons'][lesson_key] = {
                'metadata': lesson['metadata'],
                'stats': lesson['stats'],
                'questions_by_type': dang_groups
            }
        
        output_file = os.path.join(output_dir, 'index_by_category.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Lưu mục lục JSON: {output_file}")
        return output_file
    
    def generate_index_markdown(self, output_dir: str = 'output'):
        """Tạo mục lục Markdown"""
        os.makedirs(output_dir, exist_ok=True)
        
        md_lines = []
        md_lines.append("# 📚 Mục lục câu hỏi phân dạng\n")
        md_lines.append(f"**Tổng: {sum(ls['stats']['total'] for ls in self.lessons.values())} câu**\n")
        
        # Mục lục tổng quát
        md_lines.append("## 📋 Danh sách bài học\n")
        total_by_type = defaultdict(int)
        total_by_level = defaultdict(int)
        
        for lesson_key in sorted(self.lessons.keys()):
            lesson = self.lessons[lesson_key]
            stats = lesson['stats']
            total = stats['total']
            
            md_lines.append(f"- **{lesson['metadata']['bai']}** - {total} câu")
            
            for qtype in ['DS', 'TN', 'TL', 'TLN']:
                count = stats['by_type'].get(qtype, 0)
                if count > 0:
                    total_by_type[qtype] += count
                    md_lines.append(f"  - {self.QUESTION_TYPES[qtype]}: {count}")
            
            md_lines.append("")
        
        # Thống kê tổng
        md_lines.append("\n## 📊 Thống kê tổng hợp\n")
        md_lines.append("| Loại câu | Số lượng | Tỷ lệ |")
        md_lines.append("|----------|----------|-------|")
        
        total_questions = sum(self.lessons[k]['stats']['total'] for k in self.lessons.keys())
        for qtype in ['DS', 'TN', 'TL', 'TLN']:
            count = total_by_type.get(qtype, 0)
            pct = (count / total_questions * 100) if total_questions > 0 else 0
            md_lines.append(f"| {self.QUESTION_TYPES[qtype]} | {count} | {pct:.1f}% |")
        
        # Chi tiết từng bài
        md_lines.append("\n## 🎯 Chi tiết phân dạng\n")
        
        for lesson_key in sorted(self.lessons.keys()):
            lesson = self.lessons[lesson_key]
            meta = lesson['metadata']
            
            md_lines.append(f"\n### {meta['bai']}\n")
            md_lines.append(f"- **Môn**: {meta['mon']}")
            md_lines.append(f"- **Lớp**: {meta['lop']}")
            md_lines.append(f"- **Chương**: {meta['chuong']}")
            md_lines.append(f"- **Tổng câu**: {lesson['stats']['total']}\n")
            
            md_lines.append("| Loại | Mức độ | Số câu | Tỷ lệ |")
            md_lines.append("|------|--------|--------|-------|")
            
            for qtype in ['DS', 'TN', 'TL', 'TLN']:
                for level in ['NB', 'TH', 'VD', 'VDC']:
                    cat = f"{qtype}-{level}"
                    count = lesson['stats']['by_category'].get(cat, 0)
                    if count > 0:
                        pct = (count / lesson['stats']['total'] * 100)
                        type_name = self.QUESTION_TYPES[qtype]
                        level_name = self.DIFFICULTY_LEVELS[level]
                        md_lines.append(f"| {type_name} | {level_name} | {count} | {pct:.1f}% |")
        
        output_file = os.path.join(output_dir, 'INDEX_PHAN_DANG.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        
        print(f"✅ Lưu mục lục Markdown: {output_file}")
        return output_file
    
    def generate_index_html(self, output_dir: str = 'output'):
        """Tạo mục lục HTML interactif"""
        os.makedirs(output_dir, exist_ok=True)
        
        total_questions = sum(ls['stats']['total'] for ls in self.lessons.values())
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Mục lục bài tập phân dạng</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container { max-width: 1200px; margin: 0 auto; }
                header { 
                    background: white; 
                    padding: 30px; 
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    margin-bottom: 30px;
                }
                h1 { color: #333; margin-bottom: 10px; }
                .stats-bar { 
                    display: flex; 
                    gap: 20px; 
                    margin-top: 20px;
                    flex-wrap: wrap;
                }
                .stat-card {
                    flex: 1;
                    min-width: 150px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                }
                .stat-number { font-size: 2em; font-weight: bold; }
                .stat-label { font-size: 0.9em; opacity: 0.9; }
                .lessons-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                }
                .lesson-card {
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    transition: transform 0.3s;
                }
                .lesson-card:hover { transform: translateY(-5px); }
                .lesson-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px;
                }
                .lesson-title { font-weight: bold; font-size: 1.1em; }
                .lesson-info { font-size: 0.85em; opacity: 0.9; margin-top: 5px; }
                .lesson-body { padding: 15px; }
                .type-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 8px;
                    margin: 5px 0;
                    background: #f5f5f5;
                    border-left: 4px solid #667eea;
                    border-radius: 4px;
                }
                .type-item.DS { border-left-color: #FF6B6B; }
                .type-item.TN { border-left-color: #4ECDC4; }
                .type-item.TL { border-left-color: #45B7D1; }
                .type-item.TLN { border-left-color: #FFA07A; }
                .type-name { font-weight: 500; }
                .type-count { 
                    background: #667eea; 
                    color: white; 
                    padding: 2px 8px; 
                    border-radius: 12px;
                    font-size: 0.9em;
                }
                footer {
                    text-align: center;
                    color: white;
                    margin-top: 40px;
                    padding: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>📚 Mục lục Bài Tập Phân Dạng</h1>
                    <div class="stats-bar">
                        <div class="stat-card">
                            <div class="stat-number">""" + str(len(self.lessons)) + """</div>
                            <div class="stat-label">Bài học</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">""" + str(total_questions) + """</div>
                            <div class="stat-label">Câu hỏi</div>
                        </div>
                    </div>
                </header>
                
                <div class="lessons-grid">
        """
        
        for lesson_key in sorted(self.lessons.keys()):
            lesson = self.lessons[lesson_key]
            meta = lesson['metadata']
            stats = lesson['stats']
            
            html += f"""
                    <div class="lesson-card">
                        <div class="lesson-header">
                            <div class="lesson-title">{meta['bai']}</div>
                            <div class="lesson-info">{meta['mon']} - Lớp {meta['lop']}</div>
                        </div>
                        <div class="lesson-body">
                            <div style="font-weight: bold; margin-bottom: 10px; color: #333;">
                                Tổng: {stats['total']} câu
                            </div>
            """
            
            for qtype in ['DS', 'TN', 'TL', 'TLN']:
                count = stats['by_type'].get(qtype, 0)
                type_name = self.QUESTION_TYPES[qtype]
                html += f"""
                            <div class="type-item {qtype}">
                                <span class="type-name">{qtype} - {type_name}</span>
                                <span class="type-count">{count}</span>
                            </div>
                """
            
            html += """
                        </div>
                    </div>
            """
        
        html += """
                </div>
            </div>
            <footer>
                <p>Được tạo tự động bằng script phân dạng bài tập</p>
                <p>© 2026 Ứng dụng luyện đề Vật lý</p>
            </footer>
        </body>
        </html>
        """
        
        output_file = os.path.join(output_dir, 'index_phan_dang.html')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Lưu mục lục HTML: {output_file}")
        return output_file
    
    def print_summary(self):
        """In bảng tóm tắt"""
        print(f"\n{'='*80}")
        print("📋 BẢNG TÓM TẮT PHÂN DẠNG")
        print(f"{'='*80}\n")
        
        print(f"{'Bài học':<40} {'Tổng':>6} {'DS':>5} {'TN':>5} {'TL':>5} {'TLN':>5}")
        print(f"{'-'*80}")
        
        for lesson_key in sorted(self.lessons.keys()):
            lesson = self.lessons[lesson_key]
            stats = lesson['stats']
            
            bai = lesson['metadata']['bai'][:38]
            print(f"{bai:<40} {stats['total']:>6} "
                  f"{stats['by_type'].get('DS', 0):>5} "
                  f"{stats['by_type'].get('TN', 0):>5} "
                  f"{stats['by_type'].get('TL', 0):>5} "
                  f"{stats['by_type'].get('TLN', 0):>5}")


def main():
    """Hàm chính"""
    print("\n🚀 Bắt đầu phân dạng bài tập...\n")
    
    categorizer = QuestionCategorizer()
    
    # Tìm tất cả file de.tex
    base_dir = Path('ngan-hang')
    if not base_dir.exists():
        print("❌ Không tìm thấy thư mục 'ngan-hang'")
        return
    
    tex_files = sorted(list(base_dir.rglob('de.tex')))
    print(f"🔍 Tìm thấy {len(tex_files)} file TeX\n")
    
    # Phân loại từng file
    for tex_file in tex_files:
        categorizer.classify_file(str(tex_file))
    
    # In bảng tóm tắt
    categorizer.print_summary()
    
    # Xuất kết quả
    print(f"\n{'='*80}")
    print("📤 XUẤT KẾT QUẢ")
    print(f"{'='*80}\n")
    
    categorizer.generate_index_json('output')
    categorizer.generate_index_markdown('output')
    categorizer.generate_index_html('output')
    
    print(f"\n✅ Hoàn thành! Kiểm tra thư mục 'output/'")


if __name__ == '__main__':
    main()
