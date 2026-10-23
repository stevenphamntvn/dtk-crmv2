# Phương án sync dự kiến

Ngày ghi nhận: 22/10/2026.

**Trạng thái: đang thảo luận, chưa chốt thiết kế và chưa triển khai.**
Tài liệu ghi lại ý tưởng để phân tích chi tiết ở một đợt làm việc sau.
Không xem tài liệu này là yêu cầu tự triển khai toàn bộ cơ chế sync mới.

## Mục tiêu và cách sử dụng mong muốn

- Mỗi thiết bị (máy A, máy B, laptop) có dữ liệu local riêng và làm việc offline.
- Google Sheets (GS) là nơi trao đổi dữ liệu chung; app Online cũng tham gia đồng bộ.
- Khi mở app, kiểm tra GS. Nếu có bản mới, thông báo và có nút xem thay đổi.
- Người dùng kiểm tra báo cáo rồi chủ động đồng ý tải về; không tự ghi đè.
- Cuối buổi, người dùng nhấn Sync, xem báo cáo rồi xác nhận đưa thay đổi lên GS.
- Ghi nhận thiết bị hoặc Online đã thay đổi dữ liệu và thời gian thay đổi.

## Ý tưởng ban đầu của người dùng

1. Khi sửa khách hàng hoặc thông tin gửi nhà, luôn ghi thời gian sửa và thiết bị.
2. Mỗi thiết bị có cờ `sync=true/false` và thời điểm sync.
3. Khi mở app, đối chiếu thời gian sửa với thời gian sync để xác định trạng thái.
4. So sánh thời gian sync của thiết bị với Online để đề xuất upload/download.

## Điều chỉnh được đề xuất trong thảo luận

Các điểm sau là đề xuất, cần duyệt chi tiết trước khi triển khai:

- Dùng **mã phiên bản dữ liệu trên GS** làm căn cứ xác định dữ liệu mới.
  Thời gian kiểm tra hoặc sync mới hơn không có nghĩa dữ liệu mới hơn;
  đồng hồ thiết bị có thể lệch.
- Mỗi thiết bị nhớ phiên bản GS đã đồng bộ thành công (`base_version`).
- GS có phiên bản hiện tại (`cloud_version`), tăng sau một đợt ghi thành công.
- `sync=false`: còn thay đổi local chưa được GS xác nhận.
- `sync=true`: đồng bộ thành công và không còn thay đổi chưa gửi tại thời điểm đó.
  Không suy ra thành công chỉ từ việc thời gian sửa trước thời gian sync.
- Ghi nhận từng thao tác thêm/sửa/xóa, nguồn thiết bị, thời gian và phiên bản gốc.
- Thời gian do server ghi nhận phục vụ đối chiếu; không chỉ dùng giờ máy để chọn bản thắng.

## Bảng quyết định dự kiến

| Trạng thái thiết bị | So sánh phiên bản | Hướng xử lý đề xuất |
| --- | --- | --- |
| Không có thay đổi chưa gửi | `base_version == cloud_version` | Đã cập nhật |
| Không có thay đổi chưa gửi | GS mới hơn | Xem báo cáo, xác nhận tải về |
| Có thay đổi chưa gửi | GS chưa đổi kể từ lần đồng bộ trước | Xem báo cáo, xác nhận upload |
| Có thay đổi chưa gửi | GS cũng đã đổi | Đối chiếu hai bên, giải quyết xung đột trước khi ghi |

Nếu phiên bản local lớn hơn GS, cần kiểm tra bất thường/khôi phục bản sao;
không tự coi local là nguồn đúng.

## Các vấn đề phải thiết kế chi tiết sau

- Định danh thiết bị, bản ghi và thao tác; tránh hai máy cùng tạo `KID_010`
  cho hai khách khác nhau. Giữ liên kết nhật ký khi đổi hoặc ánh xạ KID.
- Nhập hợp nhất lần đầu từ các file local hiện có; không mặc định cùng KID là cùng người.
- Theo dõi thay đổi ở tất cả đường ghi: thêm/sửa khách, phân loại, ghi chú,
  bộ lọc BLK, lịch gửi, trạng thái gửi, phản hồi và thao tác xóa.
- Phân biệt chưa có dữ liệu với chủ động xóa; có dấu xóa để tránh hồi sinh bản ghi.
- Gộp hai thay đổi ở hai trường khác nhau; cùng sửa một trường thì cho người dùng chọn.
- Gửi lại sau mất mạng không tạo dữ liệu trùng; chỉ đánh dấu sync sau xác nhận thành công.
- Kiểm tra lại phiên bản ngay lúc ghi để phát hiện máy khác vừa upload trong lúc xem báo cáo.
- Quyết định cách ghi tuần tự/giao dịch trung tâm; không để nhiều máy tự đọc rồi ghi đè cả sheet.
- Thao tác sửa tay trên GS, dữ liệu rỗng, khôi phục backup và thay đổi cấu trúc cột.
- Phạm vi dữ liệu dùng chung và dữ liệu riêng thiết bị (khách cuối cùng, tùy chọn giao diện).
- Xác thực, quyền truy cập, nhật ký sync và khả năng lưu bền của app Online.

## Cơ chế hiện tại và phạm vi thay đổi đợt này

- Push hiện tại xóa nội dung hai sheet `MyKID`, `KID_log`, rồi ghi toàn bộ local lên.
- Pull hiện tại ghi đè CSV bằng dữ liệu GS khi bảng nguồn có dòng dữ liệu;
  nếu bảng nguồn rỗng thì giữ file local hiện có.
- Đợt này **chỉ cải thiện báo cáo trước xác nhận**, chưa áp dụng phiên bản,
  cờ sync, tự kiểm tra khi mở app hoặc gộp dữ liệu nhiều thiết bị.
- Báo cáo phải nêu khách/nhật ký nào và trường nào thay đổi, có hai cột Local/Online.
- Thêm: màu xanh. Bỏ: màu đỏ. Sửa: bỏ giá trị cũ màu đỏ, thêm giá trị mới màu xanh.
- Màu dựa trên chiều sync đang chọn. Ví dụ Online có khách C chưa có ở Local:
  Pull hiển thị khách C màu xanh ở Online, để thêm vào Local;
  Push hiển thị khách C màu đỏ ở Online, vì bản local sẽ loại khách đó khỏi GS.
- Xem báo cáo không ghi dữ liệu. Chỉ thực hiện khi người dùng bấm xác nhận.

## Kiểm thử cần có khi triển khai sync mới

- Hai máy thêm hai khách offline, kể cả trùng KID hiển thị.
- Hai máy sửa hai khách khác nhau, hai trường khác nhau hoặc cùng một trường.
- Xóa trên máy A, máy B giữ bản cũ; không đưa bản đã xóa trở lại ngoài ý muốn.
- Mất mạng, gửi lặp, sync thất bại một phần, đồng hồ lệch.
- GS đổi sau khi mở báo cáo nhưng trước khi xác nhận.
- Đồng bộ với app Online, khởi động lại và khôi phục backup.

Chỉ triển khai sau khi thống nhất quy tắc xung đột, định danh, nguồn dữ liệu chính
và kế hoạch chuyển đổi các file local hiện tại.
