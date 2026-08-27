#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script phân loại câu hỏi theo từng bài học
Classifies questions by lesson and generates organized reports
"""

import re
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional
import csv

class LessonQuestionClassifier:
    """Phân loại câu hỏi theo từng bài học"""
    
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
            'mon': '',
            'lop': '',
            'chuong': '',
            'bai': '',
            'questions': [],
            'stats': {}
        })
    
    def extract_metadata_from_path(self, filepath: str) -> Dict:
        """Trích xuất thông tin từ đường dẫn file"""
        parts = Path(filepath).parts
        
        metadata = {
            'mon': '',
            'lop': '',
            'chuong': '',
            'bai': ''
        }
        
        if len(parts) >= 2:
            metadata['mon'] = parts[0]  # Môn (Vật lý, Toán...)
        if len(parts) >= 3:
            # Trích xuất số lớp từ "Lớp 11" -> "11"
            lop_match = re.search(r'Lớp\s+(\d+)', parts[2])
            metadata['lop'] = lop_match.group(1) if lop_match else parts[2]
        if len(parts) >= 4:
            metadata['chuong'] = parts[3]
        if len(parts) >= 5:
            metadata['bai'] = parts[4]
        
        return metadata
    
    def extract_info_from_tex(self, content: str) -> Dict:
        """Trích xuất thông tin từ file TeX"""
        info = {
            'mon': '',
            'lop': '',
            'chuong': '',
            'bai': '',
            'so_cau': 0
        }
        
        # Tìm các dòng comment ở đầu file
        lines = content.split('\n')[:10]
        for line in lines:
            if '% Môn:' in line:
                info['mon'] = line.split('% Môn:')[1].strip()
            elif '% Lớp:' in line:
                info['lop'] = line.split('% Lớp:')[1].strip()
            elif '% Chương:' in line:
                info['chuong'] = line.split('% Chương:')[1].strip()
            elif '% Bài:' in line:
                info['bai'] = line.split('% Bài:')[1].strip()
            elif '% Số câu:' in line:
                try:
                    info['so_cau'] = int(line.split('% Số câu:')[1].strip())
                except:
                    pass
        
        return info
    
    def parse_question(self, block: str) -> Optional[Dict]:
        """Phân tích một câu hỏi"""
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
        
        # Trích xuất mức độ
        level_match = re.search(r'%\s*Mức:\s*([A-Za-z0-9]+)', block)
        level = level_match.group(1) if level_match else None
        
        # Trích xuất dạng bài
        dangbt_match = re.search(r'\\dangbt\{([^}]+)\}', block)
        question_desc = dangbt_match.group(1) if dangbt_match else ""
        
        return {
            'id': qid,
            'type': qtype,
            'level': level,
            'description': question_desc
        }
    
    def parse_tex_file(self, filepath: str) -> List[Dict]:
        """Phân tích file TeX"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Lỗi đọc file {filepath}: {e}")
            return []
        
        questions = []
        
        # Chia thành các khối câu hỏi
        blocks = re.split(r'%\s*=====\s*Câu\s+\d+\s*=====', content)
        
        for block in blocks[1:]:
            q = self.parse_question(block)
            if q:
                questions.append(q)
        
        return questions
    
    def classify_file(self, filepath: str):
        """Phân loại file và lưu vào lesson"""
        print(f"📄 Xử lý: {filepath}")
        
        # Đọc file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            return
        
        # Trích xuất thông tin
        metadata = self.extract_info_from_tex(content)
        questions = self.parse_tex_file(filepath)
        
        # Tạo khóa cho lesson
        lesson_key = metadata['bai']
        
        # Lưu thông tin
        self.lessons[lesson_key]['file'] = str(filepath)
        self.lessons[lesson_key]['mon'] = metadata['mon']
        self.lessons[lesson_key]['lop'] = metadata['lop']
        self.lessons[lesson_key]['chuong'] = metadata['chuong']
        self.lessons[lesson_key]['bai'] = metadata['bai']
        self.lessons[lesson_key]['questions'] = questions
        
        # Tính thống kê
        self.lessons[lesson_key]['stats'] = self._calculate_stats(questions)
        
        print(f"✅ Phân loại xong: {metadata['bai']}")
        print(f"   - Tổng câu: {len(questions)}")
    
    def _calculate_stats(self, questions: List[Dict]) -> Dict:
        """Tính thống kê cho một bài"""
        stats = {
            'total': len(questions),
            'by_type': defaultdict(int),
            'by_level': defaultdict(int),
            'by_type_level': defaultdict(int)
        }
        
        for q in questions:
            if q['type']:
                stats['by_type'][q['type']] += 1
            if q['level']:
                stats['by_level'][q['level']] += 1
            if q['type'] and q['level']:
                stats['by_type_level'][f"{q['type']}-{q['level']}"] += 1
        
        return dict(stats)
    
    def print_lesson_stats(self, lesson_key: str, lesson_data: Dict):
        """In thống kê cho một bài"""
        print(f"\n{'='*70}")
        print(f"📚 {lesson_data['bai']}")
        print(f"   Môn: {lesson_data['mon']} | Lớp: {lesson_data['lop']}")
        print(f"{'='*70}")
        
        stats = lesson_data['stats']
        total = stats['total']
        
        print(f"\n📊 Tổng số câu: {total}")
        
        print(f"\n📌 Theo loại câu:")
        for qtype in ['DS', 'TN', 'TL', 'TLN']:
            count = stats['by_type'].get(qtype, 0)
            pct = (count / total * 100) if total > 0 else 0
            type_name = self.QUESTION_TYPES.get(qtype, '?')
            bar = '█' * int(pct / 2)
            print(f"   {qtype:5} ({type_name:10}): {count:3} ({pct:5.1f}%) {bar}")
        
        print(f"\n📚 Theo mức độ:")
        for level in ['NB', 'TH', 'VD', 'VDC']:
            count = stats['by_level'].get(level, 0)
            pct = (count / total * 100) if total > 0 else 0
            level_name = self.DIFFICULTY_LEVELS.get(level, '?')
            bar = '█' * int(pct / 2)
            print(f"   {level:5} ({level_name:10}): {count:3} ({pct:5.1f}%) {bar}")
        
        print(f"\n🎯 Kết hợp loại & mức độ:")
        for combo in ['DS-NB', 'DS-TH', 'DS-VD', 'DS-VDC', 
                      'TN-NB', 'TN-TH', 'TN-VD', 'TN-VDC',
                      'TL-NB', 'TL-TH', 'TL-VD', 'TL-VDC',
                      'TLN-NB', 'TLN-TH', 'TLN-VD', 'TLN-VDC']:
            count = stats['by_type_level'].get(combo, 0)
            if count > 0:
                pct = (count / total * 100)
                print(f"   {combo}: {count:3} ({pct:5.1f}%)")
    
    def export_lesson_json(self, output_dir: str = 'output'):
        """Xuất kết quả thành JSON theo từng bài"""
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, 'questions_by_lesson.json')
        
        # Chuyển defaultdict thành dict thường
        export_data = {}
        for lesson_key, lesson_data in self.lessons.items():
            export_data[lesson_key] = {
                'file': lesson_data['file'],
                'mon': lesson_data['mon'],
                'lop': lesson_data['lop'],
                'chuong': lesson_data['chuong'],
                'bai': lesson_data['bai'],
                'questions': lesson_data['questions'],
                'stats': {k: dict(v) if isinstance(v, defaultdict) else v 
                         for k, v in lesson_data['stats'].items()}
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Lưu JSON: {output_file}")
    
    def export_lesson_csv(self, output_dir: str = 'output'):
        """Xuất kết quả thành CSV"""
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, 'questions_by_lesson.csv')
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Bài học', 'ID câu', 'Loại', 'Mức độ', 'Mô tả'])
            
            for lesson_key, lesson_data in sorted(self.lessons.items()):
                bai = lesson_data['bai']
                for q in lesson_data['questions']:
                    writer.writerow([
                        bai,
                        q['id'],
                        q['type'],
                        q['level'],
                        q['description']
                    ])
        
        print(f"✅ Lưu CSV: {output_file}")
    
    def export_summary_csv(self, output_dir: str = 'output'):
        """Xuất bảng tóm tắt theo từng bài"""
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, 'lesson_summary.csv')
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Bài học', 'Tổng cộng',
                'DS', 'TN', 'TL', 'TLN',
                'NB', 'TH', 'VD', 'VDC'
            ])
            
            for lesson_key in sorted(self.lessons.keys()):
                lesson_data = self.lessons[lesson_key]
                stats = lesson_data['stats']
                
                row = [
                    lesson_data['bai'],
                    stats['total'],
                    stats['by_type'].get('DS', 0),
                    stats['by_type'].get('TN', 0),
                    stats['by_type'].get('TL', 0),
                    stats['by_type'].get('TLN', 0),
                    stats['by_level'].get('NB', 0),
                    stats['by_level'].get('TH', 0),
                    stats['by_level'].get('VD', 0),
                    stats['by_level'].get('VDC', 0)
                ]
                writer.writerow(row)
        
        print(f"✅ Lưu bảng tóm tắt: {output_file}")
    
    def generate_html_report(self, output_dir: str = 'output'):
        """Tạo báo cáo HTML"""
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, 'lesson_report.html')
        
        html_parts = []
        html_parts.append("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Phân loại câu hỏi theo bài học</title>
            <style>
                * { margin: 0; padding: 0; }
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       padding: 20px; }
                .container { max-width: 1400px; margin: 0 auto; }
                h1 { color: white; text-align: center; margin-bottom: 30px; 
                     text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
                .lesson-card { background: white; border-radius: 8px; margin-bottom: 20px;
                              box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }
                .lesson-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                color: white; padding: 15px 20px; }
                .lesson-title { font-size: 1.3em; font-weight: bold; }
                .lesson-info { font-size: 0.9em; opacity: 0.9; margin-top: 5px; }
                .lesson-body { padding: 20px; }
                .stat-row { display: flex; justify-content: space-between; margin: 10px 0;
                           padding: 8px; background: #f5f5f5; border-radius: 4px; }
                .stat-label { font-weight: 500; flex: 1; }
                .stat-bar { flex: 2; margin: 0 20px; }
                .progress-bar { height: 20px; background: #e0e0e0; border-radius: 10px;
                               overflow: hidden; }
                .progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2);
                                display: flex; align-items: center; justify-content: center;
                                color: white; font-size: 0.8em; font-weight: bold; }
                .stat-value { text-align: right; font-weight: bold; min-width: 60px; }
                .type-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
                .type-box { background: #f9f9f9; padding: 10px; border-left: 4px solid #667eea; }
                .type-box.DS { border-left-color: #FF6B6B; }
                .type-box.TN { border-left-color: #4ECDC4; }
                .type-box.TL { border-left-color: #45B7D1; }
                .type-box.TLN { border-left-color: #FFA07A; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Báo cáo phân loại câu hỏi theo bài học</h1>
        """)
        
        # Thêm thông tin từng bài
        for lesson_key in sorted(self.lessons.keys()):
            lesson_data = self.lessons[lesson_key]
            stats = lesson_data['stats']
            total = stats['total']
            
            html_parts.append(f"""
            <div class="lesson-card">
                <div class="lesson-header">
                    <div class="lesson-title">📚 {lesson_data['bai']}</div>
                    <div class="lesson-info">{lesson_data['mon']} - Lớp {lesson_data['lop']}</div>
                </div>
                <div class="lesson-body">
                    <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 15px; color: #333;">
                        Tổng: {total} câu
                    </div>
            """)
            
            # Loại câu
            html_parts.append('<div class="type-grid">')
            for qtype in ['DS', 'TN', 'TL', 'TLN']:
                count = stats['by_type'].get(qtype, 0)
                pct = (count / total * 100) if total > 0 else 0
                type_name = self.QUESTION_TYPES.get(qtype, qtype)
                html_parts.append(f"""
                <div class="type-box {qtype}">
                    <div style="font-weight: bold; margin-bottom: 5px;">{qtype} - {type_name}</div>
                    <div style="font-size: 1.2em; color: #333;">{count} ({pct:.1f}%)</div>
                    <div style="height: 8px; background: #e0e0e0; border-radius: 4px; margin-top: 5px;">
                        <div style="height: 100%; width: {pct}%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 4px;"></div>
                    </div>
                </div>
                """)
            html_parts.append('</div>')
            
            # Mức độ
            html_parts.append('<div style="margin-top: 20px;"><div style="font-weight: bold; margin-bottom: 10px;">Theo mức độ:</div>')
            for level in ['NB', 'TH', 'VD', 'VDC']:
                count = stats['by_level'].get(level, 0)
                pct = (count / total * 100) if total > 0 else 0
                level_name = self.DIFFICULTY_LEVELS.get(level, level)
                html_parts.append(f"""
                <div class="stat-row">
                    <div class="stat-label">{level} - {level_name}</div>
                    <div class="stat-bar">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {pct}%;">{count}</div>
                        </div>
                    </div>
                    <div class="stat-value">{pct:.1f}%</div>
                </div>
                """)
            html_parts.append('</div>')
            
            html_parts.append('</div></div>')
        
        html_parts.append("""
            </div>
        </body>
        </html>
        """)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_parts))
        
        print(f"✅ Lưu HTML report: {output_file}")


def main():
    """Hàm chính"""
    classifier = LessonQuestionClassifier()
    
    # Tìm tất cả file de.tex
    base_dir = Path('ngan-hang')
    if not base_dir.exists():
        print("❌ Không tìm thấy thư mục 'ngan-hang'")
        return
    
    tex_files = sorted(list(base_dir.rglob('de.tex')))
    print(f"🔍 Tìm thấy {len(tex_files)} file TeX\n")
    
    # Phân loại từng file
    for tex_file in tex_files:
        classifier.classify_file(str(tex_file))
    
    # In thống kê từng bài
    print(f"\n{'='*70}")
    print("📋 THỐNG KÊ CHI TIẾT THEO BÀI HỌC")
    print(f"{'='*70}")
    
    for lesson_key in sorted(classifier.lessons.keys()):
        classifier.print_lesson_stats(lesson_key, classifier.lessons[lesson_key])
    
    # Xuất kết quả
    print(f"\n{'='*70}")
    print("📤 XUẤT KẾT QUẢ")
    print(f"{'='*70}\n")
    
    classifier.export_lesson_json()
    classifier.export_lesson_csv()
    classifier.export_summary_csv()
    classifier.generate_html_report()
    
    print(f"\n✅ Hoàn thành!")


if __name__ == '__main__':
    main()
