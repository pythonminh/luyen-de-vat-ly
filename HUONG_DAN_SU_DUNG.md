# 📚 Hướng dẫn sử dụng Script Phân loại Bài tập

## 🎯 Tổng quan

Repository này chứa 3 script Python giúp tự động phân loại câu hỏi từ các file TeX:

| Script | Chức năng | Output |
|--------|----------|--------|
| `classify_questions.py` | Phân loại chi tiết từng file | JSON, CSV, HTML |
| `classify_by_lesson.py` | Phân loại theo từng bài học | JSON, CSV, bảng tóm tắt HTML |
| `auto_categorize.py` | Tạo mục lục tất cả bài | JSON, Markdown, HTML |

---

## 📦 Cài đặt

### 1. Yêu cầu
- Python 3.7+
- Không cần thư viện ngoài (chỉ dùng built-in modules)

### 2. Clone repository
```bash
git clone https://github.com/pythonminh/luyen-de-vat-ly.git
cd luyen-de-vat-ly
```

---

## 🚀 Cách sử dụng

### **Script 1: Phân loại từng file** (`classify_questions.py`)

#### **Cách chạy:**
```bash
python scripts/classify_questions.py
```

#### **Tính năng:**
- ✅ Phân loại câu hỏi theo loại (DS, TN, TL, TLN)
- ✅ Phân loại theo mức độ (NB, TH, VD, VDC)
- ✅ Xuất kết quả chi tiết

#### **Output:**
```
Các file sẽ được tạo tại cùng thư mục với file TeX:
├── de_classification.json      # Chi tiết từng câu
├── de_classification.csv       # Dạng bảng
└── reports/
    └── classification_report.html    # Báo cáo đẹp
```

#### **Ví dụ output console:**
```
============================================================
📊 THỐNG KÊ: L11C1B3
============================================================

✓ Tổng số câu: 178

📌 Phân loại theo loại câu:
   DS    (Đúng/Sai                    ):  45 câu ( 25.3%)
   TN    (Trắc nghiệm                 ):  44 câu ( 24.7%)
   TL    (Tự luận                     ):  45 câu ( 25.3%)
   TLN   (Tự luận ngắn                ):  44 câu ( 24.7%)

📚 Phân loại theo mức độ:
   NB (Nhận biết                  ):  22 câu ( 12.4%)
   TH (Thông hiểu                 ):  57 câu ( 32.0%)
   VD (Vận dụng                   ):  68 câu ( 38.2%)
   VDC (Vận dụng cao              ):  31 câu ( 17.4%)
```

---

### **Script 2: Phân loại theo bài học** (`classify_by_lesson.py`)

#### **Cách chạy:**
```bash
python scripts/classify_by_lesson.py
```

#### **Tính năng:**
- ✅ Phân loại TẤT CẢ bài học
- ✅ Tạo bảng tóm tắt chi tiết
- ✅ Xuất báo cáo HTML trực quan

#### **Output:**
```
output/
├── questions_by_lesson.json       # Chi tiết từng bài
├── questions_by_lesson.csv        # Danh sách đầy đủ
├── lesson_summary.csv             # Bảng tóm tắt (Excel)
└── lesson_report.html             # Báo cáo HTML
```

#### **Ví dụ bảng tóm tắt (lesson_summary.csv):**
```
Bài học,Tổng cộng,DS,TN,TL,TLN,NB,TH,VD,VDC
L11C1 Bài 1. Dao động điều hòa,143,36,36,36,35,18,46,55,24
L11C1 Bài 2. Mô tả dao động,224,56,56,56,56,28,72,86,38
L11C1 Bài 3. Vận tốc, gia tốc,178,45,44,45,44,22,57,68,31
```

---

### **Script 3: Tạo mục lục tất cả bài** (`auto_categorize.py`)

#### **Cách chạy:**
```bash
python scripts/auto_categorize.py
```

#### **Tính năng:**
- ✅ Tạo mục lục tất cả bài học
- ✅ Phân dạng toàn bộ câu hỏi
- ✅ Xuất 3 định dạng: JSON, Markdown, HTML

#### **Output:**
```
output/
├── index_by_category.json          # Chi tiết JSON
├── INDEX_PHAN_DANG.md              # Markdown (đọc trên GitHub)
└── index_phan_dang.html            # HTML (mở trong trình duyệt)
```

#### **Ví dụ bảng tóm tắt console:**
```
================================================================================
📋 BẢNG TÓM TẮT PHÂN DẠNG
================================================================================

Bài học                                   Tổng     DS    TN    TL   TLN
--------------------------------------------------------------------------------
L11C1 Bài 1. Dao động điều hòa            143     36    36    36    35
L11C1 Bài 2. Mô tả dao động điều hòa      224     56    56    56    56
L11C1 Bài 3. Vận tốc, gia tốc             178     45    44    45    44
L11C1 Bài 4. Bài tập về dao động          75     19    19    19    18
L11C1 Bài 5. Động năng. Thế năng          320     80    80    80    80
L11C1 Bài 6. Dao động tắt dần             9      2     2     2     3
```

---

## 📊 Giải thích các loại câu

| Mã | Tên | Ý nghĩa | Số lượng (%) |
|----|-----|---------|------------|
| **DS** | Đúng/Sai | Trắc nghiệm 4 mệnh đề Đ/S | ~25% |
| **TN** | Trắc nghiệm | 4 phương án A, B, C, D | ~25% |
| **TL** | Tự luận | Trình bày chi tiết, giải thích | ~25% |
| **TLN** | Tự luận ngắn | Chỉ nhập đáp án số | ~25% |

## 📚 Giải thích các mức độ

| Mã | Tên | Nội dung | Ví dụ |
|----|-----|---------|-------|
| **NB** | Nhận biết | Nhớ, nhận diện khái niệm | Định nghĩa dao động |
| **TH** | Thông hiểu | Giải thích, phân tích | Vì sao vật ở biên thì v=0 |
| **VD** | Vận dụng | Áp dụng công thức | Tính v_max khi biết A, ω |
| **VDC** | Vận dụng cao | Kết hợp nhiều kiến thức | Bài tập phức tạp |

---

## 📁 Cấu trúc file kết quả

### JSON Format
```json
{
  "filepath": "ngan-hang/Vật lý/.../de.tex",
  "total_questions": 143,
  "statistics": {
    "total": 143,
    "by_type": {
      "DS": 36,
      "TN": 36,
      "TL": 36,
      "TLN": 35
    },
    "by_level": {
      "NB": 18,
      "TH": 46,
      "VD": 55,
      "VDC": 24
    }
  },
  "questions": [
    {
      "id": "L11C1B1-01-DS",
      "type": "DS",
      "level": "TH",
      "type_name": "Đúng/Sai",
      "level_name": "Thông hiểu"
    }
  ]
}
```

### CSV Format
```
ID,Type,Level,Type Name,Level Name,Question Desc
L11C1B1-01-DS,DS,TH,Đúng/Sai,Thông hiểu,Khai thác các thông số từ đồ thị
L11C1B1-01-TL,TL,TH,Tự luận,Thông hiểu,Chưa có dạng
...
```

---

## 🎨 HTML Report

Mở file `index_phan_dang.html` trong trình duyệt để xem báo cáo:
- 📊 Biểu đồ phân dạng đẹp
- 🎯 Thống kê theo bài học
- 📋 Danh sách chi tiết câu hỏi

---

## 🔧 Tùy chỉnh & Mở rộng

### Thay đổi thư mục output
```python
classifier.export_json('my_output/data.json', result)
classifier.generate_html_report('my_output')
```

### Lọc câu hỏi theo mức độ
```python
# Chỉ lấy câu VD và VDC
filtered = [q for q in questions if q['level'] in ['VD', 'VDC']]
```

### Tạo báo cáo tùy chỉnh
Sửa file script và thêm:
```python
def custom_report(self):
    for lesson_key, lesson_data in self.lessons.items():
        # Viết logic tùy chỉnh ở đây
        pass
```

---

## 🐛 Troubleshooting

### Lỗi: "Không tìm thấy thư mục 'ngan-hang'"
**Giải pháp**: Đảm bảo bạn chạy script từ thư mục gốc của repository:
```bash
cd luyen-de-vat-ly
python scripts/auto_categorize.py
```

### Lỗi: "No module named..."
**Giải pháp**: Cài Python 3.7+, không cần cài thêm thư viện ngoài

### File TeX không được phân loại
**Giải pháp**: Kiểm tra file có comment đầu không:
```tex
% Môn: Vật lý
% Lớp: 11
% Bài: L11C1 Bài 1. Dao động điều hòa
% Số câu: 143
```

---

## 📞 Support

Có thắc mắc? Liên hệ:
- 📧 Email: lienminh102@gmail.com
- 💬 GitHub Issues: [luyen-de-vat-ly/issues](https://github.com/pythonminh/luyen-de-vat-ly/issues)

---

## 📝 License

Dự án này được phát hành dưới giấy phép MIT.

---

**Được tạo bởi**: @pythonminh  
**Ngày cập nhật**: 2026-08-27  
**Phiên bản**: 1.0.0
