# Học song ngữ Việt – Anh trên Lớp Học Thầy Minh

## Sử dụng

Sau khi đăng nhập và mở bài học, nhấn nút **🌐 VI/EN** ở góc dưới bên phải.

- **🇻🇳 Tiếng Việt**: dịch đoạn tiếng Anh được chọn về tiếng Việt.
- **🇬🇧 English**: dịch câu hỏi hoặc đoạn đang chọn sang tiếng Anh.
- **📚 Song ngữ**: xem đồng thời nguyên văn và bản dịch.
- **✏️ Dịch đoạn bôi đen**: dịch phần nội dung do học sinh chọn.
- **🔊 Nghe phát âm**: dùng giọng có trên trình duyệt (Web Speech API).

Bản dịch nằm trong một bảng riêng, **không ghi đè đề, phương án, đáp án hay điểm**. Lời giải không được tự động đưa vào yêu cầu dịch câu hỏi. Công thức, MathJax và số liệu được bảo vệ bằng ký hiệu tạm trong lúc dịch và được khôi phục đúng nguyên bản khi trả về. Nếu mô hình làm mất ký hiệu, hệ thống từ chối hiển thị bản dịch.

Tính năng dùng Gemini hiện có. Máy chủ có thể cấu hình biến môi trường GEMINI_API_KEY; nếu không, học sinh đã đăng nhập có thể dùng key lưu theo cơ chế Gemini sẵn có tại /member/ai. Key không được đưa vào nội dung trang hoặc bản dịch.

Trang bài HTML mở trong iframe sandbox tiếp tục cô lập. Chỉ nội dung văn bản của câu hỏi được gửi qua postMessage tới trang cha rồi từ trang cha gọi API có đăng nhập. Không nới allow-same-origin, không truyền key vào iframe.

## Kiểm tra thủ công khi duyệt PR

1. Đăng nhập tài khoản học sinh, mở /member/practice; chuyển English và kiểm tra câu hỏi + 4 phương án, số liệu, công thức vẫn đúng.
2. Chọn song ngữ và xem cả văn bản tiếng Việt + tiếng Anh; bấm Nghe.
3. Bôi đen một đoạn tiếng Anh và chuyển Tiếng Việt để dịch ngược.
4. Làm bài và chấm: kết quả giống trước khi bật song ngữ; lời giải vẫn bị khóa đến khi người học nộp.
5. Mở /member/html-practice có iframe srcdoc, chọn EN rồi dịch; thử đổi số trong iframe và dịch lại.
6. Dùng điện thoại dọc/ngang; bảng không che nút chọn đáp án khi đóng.
7. Khi không có key Gemini, hiển thị hướng dẫn nạp key; không xảy ra lỗi 500.

## Hạn chế

Dịch máy hỗ trợ hiểu bài, không thay thế bản gốc. Đề quá dài hoặc không có nội dung chữ có thể cần chọn một đoạn ngắn. Trình đọc phụ thuộc giọng tiếng Việt/Anh do thiết bị cài đặt. Dịch cần kết nối mạng và Gemini API key.

Thay đổi được đề xuất dưới dạng pull request để kiểm thử trước khi đưa lên website chính.
