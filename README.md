# Alpha Stock

Website: https://kalm-d.github.io/alpha-stock/

Tự động tải giá HOSE, HNX, UPCOM và VNINDEX lúc 15:00 giờ Việt Nam, thứ Hai đến thứ Sáu. GitHub có thể khởi chạy trễ. Một lượt tải toàn thị trường cần thêm thời gian để hoàn tất; 15:00 là giờ bắt đầu, không phải giờ hoàn tất.

Website tự nạp dữ liệu đã xuất bản, ghi rõ ngày giá và thời điểm cập nhật. Giá tại 15:00 có thể chưa chốt cuối phiên. Ngày nghỉ vẫn chạy lịch nhưng không tạo phiên giá giả. Không tự nạp demo; demo chỉ dùng khi người dùng chọn.

Nguồn: vnstock 4.0.8 / KBS, chế độ miễn phí, nghỉ 3,6 giây giữa yêu cầu. Lần đầu tải 320 phiên; các lần sau tải chồng 10 ngày, tải lại nếu phát hiện giá lịch sử đổi và đối soát toàn bộ thứ Hai. Mã tải lỗi giữ lịch sử cũ và được ghi trong trạng thái. Nếu dưới 80% yêu cầu thành công, không xuất bản thay bản cũ.

GitHub Pages dùng GitHub Actions. Dữ liệu lưu trong cache và bản website, không commit vào lịch sử mã nguồn. Chạy tay tại Actions → Cập nhật giá 15h Việt Nam → Run workflow. Chọn test_only để kiểm tra một mã mỗi sàn và VNINDEX mà không xuất bản.

Lịch GitHub có thể bị tắt sau 60 ngày kho không hoạt động; kiểm tra Actions và bật lại khi cần. Danh mục, watchlist và thiết lập vẫn lưu riêng trên trình duyệt. Không lưu API key hoặc dữ liệu cá nhân vào kho công khai.
