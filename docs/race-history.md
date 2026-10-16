# Luyện đổi số và lịch sử bài làm

- Đáp án số không nguyên: làm tròn đến 2 chữ số sau dấu phẩy, ví dụ `8,19`.
- Câu nhiều kết quả: dùng dấu `;`, ví dụ `53,13; 17,41`.
- Chấm bài cũng chấp nhận dấu chấm thập phân và biểu thức chính xác tương đương.
- Đầu mút của đáp án dạng khoảng phải giữ phân số chính xác, tránh thay đổi biên của tập hợp.
- Quy tắc và đáp án đã làm tròn được lưu ngay trong từng đề riêng; bài cũ giữ quy tắc của bài cũ.

ADMIN mở **Thi đua luyện đề → Lịch sử bài làm học sinh**, lọc ngày / tên học sinh / phòng, rồi mở từng học sinh để xem số liệu riêng, bài làm, lời giải, đúng/sai, thời gian bắt đầu/nộp và các lần lưu câu trả lời.

## Lưu lâu dài

SQLite phục vụ phòng đang hoạt động. Bản sao đầy đủ của từng phòng được nén và mã hóa xác thực Fernet trước khi lưu lên nhánh `race-results-archive` trong cùng kho GitHub. Nhánh này độc lập với `main`, không kích hoạt triển khai ứng dụng. Tên học sinh, đề và câu trả lời không được ghi lên GitHub dưới dạng văn bản đọc được.

Cấu hình máy chủ:

- `GITHUB_TOKEN` (cấu hình sẵn của ứng dụng) cần quyền ghi nội dung kho.
- `PRACTICE_RACE_ARCHIVE_KEY`: khóa Fernet tạo một lần, giữ nguyên qua các lần triển khai. Không đưa khóa vào mã nguồn, tệp sao lưu hay nhật ký. Mất/thay khóa sẽ không đọc được bản lưu mã hóa cũ.
- `PRACTICE_RACE_ARCHIVE_BRANCH`: tùy chọn; mặc định `race-results-archive`.

Bản lưu được cập nhật khi tạo/tham gia/bắt đầu phòng, nộp bài, chấm hoặc kết thúc; câu trả lời nháp đồng bộ theo đợt. Chỉ hiển thị **Đã lưu lâu dài** khi cả bản phòng và chỉ mục đã ghi thành công. Mở lại lịch sử sau triển khai sẽ đọc chỉ mục và khôi phục phòng cần xem. Chỉ ADMIN sở hữu phòng được xem hoặc xuất toàn bộ bài làm.

Nếu mạng/kết nối lưu trữ lỗi, bài vẫn được giữ trong SQLite đang chạy, máy chủ tự thử lại và giao diện báo chưa đồng bộ. ADMIN có nút **Lưu lâu dài ngay** và **Tải đề và toàn bộ bài làm (.json)**. Tệp tải về chứa toàn bộ lịch sử, có thể nhập lại tại trang Lịch sử; chỉ người giữ tệp mới nên được truy cập vì đây là bản sao lưu đọc được.

`/api/race-storage-status` chỉ báo đã cấu hình / đã kiểm tra ghi-đọc thành công / có lỗi; không trả khóa hay dữ liệu học sinh.
