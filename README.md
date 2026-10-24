# DTK CRM V2

Bản phát triển độc lập tại `D:\DSH_WP\Developing\DTK_CRM_v2`.
Bản V1 tại `D:\DSH_WP\DTK_CRM` được giữ nguyên.

## Chạy trên Windows

Mở `run.bat`, truy cập http://localhost:8506. V1 tiếp tục dùng cổng riêng.
Khi máy chưa cài thư viện: `python -m pip install -r requirements.txt`.

Sidebar có **Cách xem ảnh**:

- **Thư mục Windows**: giữ nguyên cách mở Explorer của V1.
- **Ảnh trên thiết bị (trình duyệt)**: thử luồng dùng trên Android ngay trên PC.

V2 đã sao chép cache và credentials local sang thư mục riêng. Thay đổi local
ở V2 không ghi vào CSV của V1. Nút upload vẫn dùng Google Sheet hiện tại và
có báo cáo duyệt trước như V1; nếu xác nhận upload, dữ liệu online dùng chung sẽ đổi.
Chưa có thao tác upload dữ liệu nào được thực hiện khi xây dựng/kiểm thử V2.

## Ảnh trên Android và trình duyệt

1. Đồng bộ JPG về một thư mục thực trên điện thoại, giữ cấu trúc:

   ```text
   SH Total/
     Binh Thanh/<Tên đường không dấu>/<Số nhà> <Tên đường không dấu>/*.jpg
     Phu Nhuan/<Tên đường không dấu>/<Số nhà> <Tên đường không dấu>/*.jpg
   ```

2. Mở bản Cloud V2 qua HTTPS bằng Chrome mới.
3. Bấm **Chọn SH Total**. Thư mục phải có cả Bình Thạnh và Phú Nhuận;
   đối chiếu tên không phân biệt hoa thường và dấu tiếng Việt.
4. App báo OK và ghi nhớ quyền trong IndexedDB nếu trình duyệt cho phép.
5. Bấm biểu tượng ảnh ở bảng nhà hoặc Nhật ký Zalo. Có JPG thì xem tại chỗ,
   bấm để phóng lớn, vuốt hoặc bấm mũi tên để chuyển ảnh. SF và PNG không được đọc.
6. Thiếu ảnh/quyền thì dùng URL Cloud của đúng căn nhà. Nếu trình duyệt chặn
   cửa sổ bật lên, bấm **Mở ảnh Cloud**. Không có cả link thì báo chưa có ảnh.

Quyền đọc có thể hết hiệu lực sau khi đóng trình duyệt, khởi động lại, hoặc
xóa dữ liệu trang; dùng **Cấp lại quyền** hoặc chọn lại thư mục. Nút **Quên thư mục**
chỉ quên quyền, không xóa JPG. Ảnh và đường dẫn gốc không tải lên Streamlit.
Ảnh offline trong ứng dụng Google Drive chưa chắc là thư mục trình duyệt đọc được;
cần thư mục thật do công cụ đồng bộ tạo. CRM vẫn cần kết nối đến máy chủ.

Đã kiểm tra luồng giao diện trên trình duyệt PC; cần nghiệm thu trực tiếp trên
Chrome Android với thư mục ảnh thật trước khi đưa vào sử dụng chính thức.

## Một mã nguồn cho local và Cloud

- `streamlit_app.py`: entry point dùng chung.
- `crm_v2/protocol.py`: quy tắc BLK, giá, khu vực, phân khúc dùng chung.
- `crm_v2/customer_data.py`: lưu khách local dùng chung.
- `crm_v2/sync_report.py`: so sánh chi tiết, đỏ là bỏ, xanh là thêm.
- `crm_v2/photos.py` và `photo_assets/`: bộ ảnh trên trình duyệt.
- `Data/crm_app.py`: giao diện và các nghiệp vụ kế thừa; chưa tách toàn bộ file.
- `SOURCE_BASELINE.json`: SHA256 các file V1 để kiểm tra bản gốc không bị sửa.

Cloud tự dùng bộ ảnh trình duyệt; PC mặc định Explorer. Các nghiệp vụ khác
dùng cùng mã nguồn. Đồng bộ dữ liệu nhiều thiết bị theo phiên bản vẫn là
**phương án dự kiến**, xem `PHUONG_AN_SYNC_DU_KIEN.md`; chưa triển khai trong V2 này.

## Phát hành và cập nhật

Mỗi lần nâng cấp, sửa mã nguồn ở V2 và tăng `VERSION` trong `crm_v2/__init__.py`.
Chạy kiểm thử, rồi chạy `python tools/release.py` để tạo gói ZIP và SHA256.

- Cloud: deploy cùng mã nguồn/phiên bản lên **một app V2 riêng**. Điện thoại
  mở lại trang để nhận giao diện mới. Quyền thư mục là riêng từng trình duyệt.
- Local: đóng riêng tiến trình V2, mở `update.bat`, nhập đường dẫn gói ZIP.
  Có thể đối chiếu thêm SHA256 bằng lệnh
  `python tools/update.py "D:\duong-dan\ban-moi.zip" --sha256 <SHA256>`.
- Updater kiểm tra manifest, SHA256 từng file và giới hạn đường dẫn; chỉ thay mã nguồn.
  Không thay CSV, credentials, secrets hoặc `settings.local.json`.
  Mã nguồn cũ lưu tại `.updates/rollback-*`; lỗi khi áp dụng thì tự phục hồi các file đã thay.
  Sau cập nhật, cài requirements nếu có thay đổi thư viện rồi mở lại `run.bat`.

Hiện đã có đóng gói và cập nhật bằng ZIP. Chưa có URL kiểm tra bản mới/tải gói
tự động; phần này cần nối với nơi phát hành V2 sau khi tạo repository/hosting riêng.
Không deploy V2 lên app Cloud V1 hiện tại. Khi chuẩn bị repository V2,
không đưa credentials, cache, secrets, logs, `.updates` hoặc gói ZIP vào Git.

## Kiểm tra

```powershell
python -m unittest discover -s tests -v
node --test tests/test_photos.mjs
```

Các kiểm thử sử dụng dữ liệu tạm và mock; không ghi Google Sheets.

## Cập nhật 2.0.0-dev.3

Các ô Đặc điểm tự xuống hàng trên tablet để hiện đủ nhãn; màn hình PC rộng giữ một hàng. Các lựa chọn lọc được giữ nguyên.
