#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để phân loại tự động các câu hỏi từ file TeX
Clasifies questions by type (DS, TN, TL, TLN) and level (NB, TH, VD, VDC)
"""

import re
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

class QuestionClassifier:
    """Phân loại câu hỏi từ file TeX"""
    
    # Các kiểu câu hỏi
    QUESTION_TYPES = {
        'DS': 'Đúng/Sai (True/False)',
        'TN': 'Trắc nghiệm (Multiple Choice)',
        'TL': 'Tự luận (Essay)',
        'TLN': 'Tự luận ngắn (Short Answer)'
    }
    
    # Các mức độ
    DIFFICULTY_LEVELS = {
        'NB': 'Nhận biết (Knowledge)',
        'TH': 'Thông hiểu (Comprehension)',
        'VD': 'Vận dụng (Application)',
        'VDC': 'Vận dụng cao (Higher-order)'
    }
    
    def __init__(self):
        self.questions = []
        self.stats = defaultdict(int)
        
    def extract_question_id(self, content: str) -> Optional[str]:
        """Trích xuất ID câu hỏi"""
        match = re.search(r'%\s*ID:\s*([A-Za-z0-9\-]+)', content)
        return match.group(1) if match else None
    
    def extract_level(self, content: str) -> Optional[str]:
        """Trích xuất mức độ câu hỏi"""
        match = re.search(r'%\s*Mức:\s*([A-Za-z0-9]+)', content)
        return match.group(1) if match else None
    
    def extract_question_type(self, content: str) -> Optional[str]:
        """Xác định loại câu hỏi dựa trên ID hoặc cấu trúc"""
        qid = self.extract_question_id(content)
        if not qid:
            return None
        
        # Trích xuất phần cuối của ID (DS, TN, TL, TLN)
        for qtype in ['TLN', 'TL', 'DS', 'TN']:  # Kiểm tra TLN trước (để không nhầm TL)
            if qid.endswith('-' + qtype):
                return qtype
        return None
    
    def detect_question_structure(self, content: str) -> Dict[str, any]:
        """Phát hiện cấu trúc chi tiết của câu hỏi"""
        structure = {
            'has_choiceTF': bool(re.search(r'\\choiceTF', content)),
            'has_choice': bool(re.search(r'\\choice(?!\w)', content)),
            'has_shortans': bool(re.search(r'\\shortans', content)),
            'has_loigiai': bool(re.search(r'\\loigiai', content)),
            'has_itemchoice': bool(re.search(r'\\itemchoice', content)),
            'num_items': len(re.findall(r'\\item', content))
        }
        return structure
    
    def parse_tex_file(self, filepath: str) -> List[Dict]:
        """Phân tích file TeX và trích xuất các câu hỏi"""
        questions = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Lỗi đọc file {filepath}: {e}")
            return questions
        
        # Chia file thành các khối câu hỏi (mỗi khối bắt đầu với % ===== Câu X =====)
        question_blocks = re.split(r'%\s*=====\s*Câu\s+\d+\s*=====' , content)
        
        for block in question_blocks[1:]:  # Bỏ qua phần đầu
            try:
                question = self._parse_question_block(block)
                if question:
                    questions.append(question)
            except Exception as e:
                print(f"⚠️  Lỗi phân tích khối câu hỏi: {e}")
                continue
        
        return questions
    
    def _parse_question_block(self, block: str) -> Optional[Dict]:
        """Phân tích một khối câu hỏi"""
        qid = self.extract_question_id(block)
        if not qid:
            return None
        
        qtype = self.extract_question_type(block)
        level = self.extract_level(block)
        structure = self.detect_question_structure(block)
        
        # Trích xuất dạng bài (dangbt)
        dangbt_match = re.search(r'\\dangbt\{([^}]+)\}', block)
        question_type_desc = dangbt_match.group(1) if dangbt_match else "Không xác định"
        
        # Trích xuất câu hỏi chính
        ex_match = re.search(r'\\begin\{ex\}.*?([^%]+?)\\choice', block, re.DOTALL)
        if not ex_match:
            ex_match = re.search(r'\\begin\{ex\}.*?([^%]+?)\\end\{ex\}', block, re.DOTALL)
        
        question_text = ex_match.group(1).strip() if ex_match else "N/A"
        question_text = question_text[:100].strip()  # Lấy 100 ký tự đầu
        
        return {
            'id': qid,
            'type': qtype,
            'type_name': self.QUESTION_TYPES.get(qtype, 'Unknown'),
            'level': level,
            'level_name': self.DIFFICULTY_LEVELS.get(level, 'Unknown'),
            'question_desc': question_type_desc,
            'question_text': question_text,
            'structure': structure
        }
    
    def classify_file(self, filepath: str) -> Dict:
        """Phân loại tất cả câu hỏi trong file"""
        print(f"\n📄 Đang phân lo��i: {filepath}")
        
        questions = self.parse_tex_file(filepath)
        self.questions.extend(questions)
        
        # Thống kê
        stats = {
            'total': len(questions),
            'by_type': defaultdict(int),
            'by_level': defaultdict(int),
            'by_type_and_level': defaultdict(int)
        }
        
        for q in questions:
            if q['type']:
                stats['by_type'][q['type']] += 1
            if q['level']:
                stats['by_level'][q['level']] += 1
            if q['type'] and q['level']:
                stats['by_type_and_level'][f"{q['type']}-{q['level']}"] += 1
        
        return {
            'filepath': filepath,
            'questions': questions,
            'stats': dict(stats)
        }
    
    def print_stats(self, result: Dict):
        """In thống kê"""
        print(f"\n{'='*60}")
        print(f"📊 THỐNG KÊ: {Path(result['filepath']).stem}")
        print(f"{'='*60}")
        
        stats = result['stats']
        print(f"\n✓ Tổng số câu: {stats['total']}")
        
        print(f"\n📌 Phân loại theo loại câu:")
        for qtype, count in sorted(stats['by_type'].items()):
            pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            type_name = self.QUESTION_TYPES.get(qtype, qtype)
            print(f"   {qtype:5} ({type_name:30}): {count:3} câu ({pct:5.1f}%)")
        
        print(f"\n📚 Phân loại theo mức độ:")
        for level, count in sorted(stats['by_level'].items()):
            pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            level_name = self.DIFFICULTY_LEVELS.get(level, level)
            print(f"   {level:3} ({level_name:30}): {count:3} câu ({pct:5.1f}%)")
        
        print(f"\n🎯 Phân loại theo loại + mức độ:")
        for combo, count in sorted(stats['by_type_and_level'].items()):
            pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {combo:10}: {count:3} câu ({pct:5.1f}%)")
    
    def export_json(self, output_file: str, result: Dict):
        """Xuất kết quả thành JSON"""
        output_data = {
            'filepath': result['filepath'],
            'total_questions': result['stats']['total'],
            'statistics': result['stats'],
            'questions': result['questions']
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Đã lưu kết quả vào: {output_file}")
    
    def export_csv(self, output_file: str, result: Dict):
        """Xuất kết quả thành CSV"""
        import csv
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'ID', 'Type', 'Level', 'Type Name', 'Level Name', 'Question Desc', 'Question Text'
            ])
            writer.writeheader()
            
            for q in result['questions']:
                writer.writerow({
                    'ID': q['id'],
                    'Type': q['type'],
                    'Level': q['level'],
                    'Type Name': q['type_name'],
                    'Level Name': q['level_name'],
                    'Question Desc': q['question_desc'],
                    'Question Text': q['question_text']
                })
        
        print(f"✅ Đã lưu CSV vào: {output_file}")
    
    def create_report(self, output_dir: str = 'reports'):
        """Tạo báo cáo chi tiết"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Tổng hợp thống kê
        total_stats = {
            'total_questions': sum(len(r['questions']) for r in self.results),
            'by_type': defaultdict(int),
            'by_level': defaultdict(int)
        }
        
        for result in self.results:
            for q in result['questions']:
                if q['type']:
                    total_stats['by_type'][q['type']] += 1
                if q['level']:
                    total_stats['by_level'][q['level']] += 1
        
        # Tạo file báo cáo HTML
        html_content = self._generate_html_report(total_stats)
        
        report_file = os.path.join(output_dir, 'classification_report.html')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Đã tạo báo cáo: {report_file}")
    
    def _generate_html_report(self, stats: Dict) -> str:
        """Tạo HTML báo cáo"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Báo cáo phân loại câu hỏi</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
                th { background-color: #4CAF50; color: white; }
                tr:nth-child(even) { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>📊 Báo cáo phân loại câu hỏi</h1>
            <p><strong>Tổng số câu:</strong> {}</p>
            
            <h2>Phân loại theo loại câu</h2>
            <table>
                <tr><th>Loại</th><th>Số lượng</th><th>Tỷ lệ</th></tr>
                {}
            </table>
            
            <h2>Phân loại theo mức độ</h2>
            <table>
                <tr><th>Mức độ</th><th>Số lượng</th><th>Tỷ lệ</th></tr>
                {}
            </table>
        </body>
        </html>
        """
        
        total = stats['total_questions']
        
        # Phần loại câu
        type_rows = ""
        for qtype, count in sorted(stats['by_type'].items()):
            pct = (count / total * 100) if total > 0 else 0
            type_name = self.QUESTION_TYPES.get(qtype, qtype)
            type_rows += f"<tr><td>{qtype} - {type_name}</td><td>{count}</td><td>{pct:.1f}%</td></tr>"
        
        # Phần mức độ
        level_rows = ""
        for level, count in sorted(stats['by_level'].items()):
            pct = (count / total * 100) if total > 0 else 0
            level_name = self.DIFFICULTY_LEVELS.get(level, level)
            level_rows += f"<tr><td>{level} - {level_name}</td><td>{count}</td><td>{pct:.1f}%</td></tr>"
        
        return html.format(total, type_rows, level_rows)


def main():
    """Hàm chính"""
    import sys
    
    classifier = QuestionClassifier()
    classifier.results = []
    
    # Tìm tất cả file TeX
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # Mặc định tìm trong thư mục ngan-hang
        base_dir = Path('ngan-hang')
        if not base_dir.exists():
            print("❌ Không tìm thấy thư mục 'ngan-hang'")
            return
        
        tex_files = list(base_dir.rglob('de.tex'))
        print(f"🔍 Tìm thấy {len(tex_files)} file TeX")
    
    if len(sys.argv) > 1:
        tex_files = [filepath]
    else:
        tex_files = sorted(list(base_dir.rglob('de.tex')))[:3]  # Giới hạn 3 file
    
    # Phân loại từng file
    for tex_file in tex_files:
        result = classifier.classify_file(str(tex_file))
        classifier.results.append(result)
        classifier.print_stats(result)
        
        # Xuất kết quả
        output_json = str(tex_file).replace('.tex', '_classification.json')
        output_csv = str(tex_file).replace('.tex', '_classification.csv')
        
        classifier.export_json(output_json, result)
        classifier.export_csv(output_csv, result)
    
    # Tạo báo cáo tổng hợp
    if classifier.results:
        classifier.create_report()
        
        # Thống kê tổng hợp
        print(f"\n{'='*60}")
        print("📈 THỐNG KÊ TỔNG HỢP")
        print(f"{'='*60}")
        print(f"✓ Tổng số file xử lý: {len(classifier.results)}")
        print(f"✓ Tổng số câu hỏi: {sum(len(r['questions']) for r in classifier.results)}")


if __name__ == '__main__':
    main()
