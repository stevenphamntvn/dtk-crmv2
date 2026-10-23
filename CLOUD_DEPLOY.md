# Triển khai CRM V2 riêng

- Streamlit workspace được chọn: `trungpv955-design`.
- URL yêu cầu: `https://dtk-crmv2.streamlit.app/`.
- Repository nguồn: `https://github.com/stevenphamntvn/dtk-crmv2`.
- Repository đang deploy: `https://github.com/trungpv955-design/dtk-crmv2`.
- Branch: `codex/crm-v2`.
- Main file: `streamlit_app.py`.
- Python: 3.13 hoặc phiên bản được Streamlit hỗ trợ tương thích requirements.

Repository đã có mã nguồn và được công khai theo yêu cầu của chủ app.
CSV, ảnh, Google credentials và Secrets không nằm trong repository.
Ngày 24/10/2026, app đã được tạo và khởi động tại URL trên bằng Python 3.14.
Chủ app đã lưu Secrets trực tiếp. Đã kiểm tra trên Cloud: màn hình yêu cầu cấu hình
được thay bằng form đăng nhập bình thường, xác nhận app đã nhận tài khoản từ Secrets.
Chưa đăng nhập thay người dùng hoặc kiểm tra thao tác dữ liệu sau đăng nhập trên Cloud.
Service account trong file local đã được kiểm tra quyền đọc ba sheet nghiệp vụ;
không có thao tác ghi Google Sheets trong quá trình triển khai.
Streamlit yêu cầu quyền quản trị repository ngay cả khi mã nguồn công khai.
Chỉ công khai repository của `stevenphamntvn` chưa đủ để workspace `trungpv955-design`
triển khai; cần fork sang đúng tài khoản.

## Cập nhật khi dùng fork

Sửa và kiểm thử mã tại V2 rồi đẩy lên repository nguồn. Trên GitHub của
`trungpv955-design/dtk-crmv2`, dùng **Sync fork → Update branch** để nhận bản mới
trên nhánh `codex/crm-v2`; Streamlit sẽ deploy từ bản fork đó. Chỉ push repository
nguồn chưa làm app trong tài khoản trungpv cập nhật. Máy local dùng gói ZIP cùng
phiên bản theo README. Chưa cấu hình tự đồng bộ hai repository.

## Secrets

Cấu hình Google service account bằng `GOOGLE_CREDENTIALS` trong phần Advanced
settings hoặc Settings → Secrets của app V2. Chỉ dùng giao diện Secrets,
không commit JSON credentials hoặc CSV lên repository.

Tài khoản đăng nhập ứng dụng phải được cấu hình riêng:

```toml
APP_USERNAME = "admin"
APP_PASSWORD = "THAY_BANG_MAT_KHAU_RIENG"
```

Hoặc dùng bảng `[users]`. Không có cấu hình tài khoản thì V2 dừng tại màn hình
thông báo, không dùng mật khẩu mặc định từ mã nguồn V1.

Không thay đổi cấu hình, repository hoặc app Cloud V1. V2 dùng cùng Google Sheet
khi được cấu hình cùng service account; upload dữ liệu chỉ diễn ra sau bước
kiểm duyệt sync trên giao diện.

## Nghiệm thu sau khi deploy

1. Trang V2 hiển thị màn hình đăng nhập và phiên bản V2.
2. Đăng nhập bằng tài khoản đã cấu hình, dữ liệu tải từ Sheets.
3. Kiểm tra bảng khách và nhật ký Zalo; không upload dữ liệu thử lên Sheets.
4. Trên Chrome Android: chọn thư mục SH Total, cấp quyền, mở JPG tại thiết bị.
5. Căn không có JPG local: dùng link Cloud của đúng căn.

28 kiểm thử Python và 3 kiểm thử JavaScript đã đạt trước triển khai.
