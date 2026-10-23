# Triển khai CRM V2 riêng

- Streamlit workspace được chọn: `trungpv955-design`.
- URL yêu cầu: `https://dtk-crmv2.streamlit.app/`.
- Repository: `https://github.com/stevenphamntvn/dtk-crmv2`.
- Khi dùng workspace `trungpv955-design`, cần fork repository này sang GitHub
  `trungpv955-design` và chọn repository fork trong biểu mẫu deploy.
- Branch: `codex/crm-v2`.
- Main file: `streamlit_app.py`.
- Python: 3.13 hoặc phiên bản được Streamlit hỗ trợ tương thích requirements.

Repository đã có mã nguồn và được công khai theo yêu cầu của chủ app.
CSV, ảnh, Google credentials và Secrets không nằm trong repository.
Tại thời điểm chuẩn bị, tên miền còn trống; app đang được cấu hình triển khai.
Streamlit yêu cầu quyền quản trị repository ngay cả khi mã nguồn công khai.
Chỉ công khai repository của `stevenphamntvn` chưa đủ để workspace `trungpv955-design`
triển khai; cần fork sang đúng tài khoản.

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
