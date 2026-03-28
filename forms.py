import re
from datetime import date, time

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    FloatField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)

from models import User

TIME_RE = r"^([01]\d|2[0-3]):([0-5]\d)$"


def parse_time(s):
    #? parse HH:MM str to time obj
    parts = s.split(":")
    return time(int(parts[0]), int(parts[1]))


def _build_slots(start_t, close_t, interval_minutes=60):
    #? yield (start, end) time tuples starting from start_t, stepping by interval_minutes
    cursor = start_t
    while True:
        end_m = cursor.minute + interval_minutes
        end_extra_h = end_m // 60
        end_m = end_m % 60
        end_h = (cursor.hour + end_extra_h) % 24
        end_t = time(end_h, end_m)

        if end_t <= cursor:
            break
        if end_t > close_t:
            break

        yield (cursor, end_t)
        cursor = end_t


def generate_time_slots(open_time_str, close_time_str, interval_minutes=60):
    #? generate [(value_str, 'HH:MM - HH:MM'), ...] fixed-duration slots between open and close.
    open_t = parse_time(open_time_str)
    close_t = parse_time(close_time_str)

    #? build slots from :00 and :30 start minutes
    half_open = time(open_t.hour, 30)
    slots = list(_build_slots(open_t, close_t, interval_minutes))
    if half_open < close_t:
        slots += list(_build_slots(half_open, close_t, interval_minutes))

    #? sort by start time and format
    slots.sort(key=lambda p: (p[0].hour, p[0].minute))
    return [(s.strftime("%H:%M"), f"{s.strftime('%H:%M')} - {e.strftime('%H:%M')}") for s, e in slots]


def make_time_choice(start_str, end_str):
    return f"{start_str} - {end_str}"


class RegisterForm(FlaskForm):
    full_name = StringField(
        "Họ tên",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    username = StringField(
        "Tên đăng nhập",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    email = StringField(
        "Email",
        validators=[InputRequired(message="Email là bắt buộc."), Email(message="Email không hợp lệ.")],
    )
    phone = StringField(
        "Số điện thoại",
        validators=[
            Optional(),
            Regexp(
                r"^0[0-9]{9,10}$",
                message="Số điện thoại phải bắt đầu bằng 0 và có 10–11 chữ số.",
            ),
        ],
    )
    role = SelectField(
        "Loại tài khoản",
        choices=[("customer", "Người dùng"), ("owner", "Chủ hồ câu")],
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Mật khẩu",
        validators=[DataRequired(), Length(min=6, message="Mật khẩu phải có ít nhất 6 ký tự.")],
    )
    confirm_password = PasswordField(
        "Xác nhận mật khẩu",
        validators=[DataRequired(), EqualTo("password", message="Mật khẩu xác nhận không khớp.")],
    )
    submit = SubmitField("Đăng ký")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError("Tên đăng nhập đã tồn tại.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Email đã được sử dụng.")


class LoginForm(FlaskForm):
    username = StringField("Tên đăng nhập", validators=[DataRequired()])
    password = PasswordField("Mật khẩu", validators=[DataRequired()])
    submit = SubmitField("Đăng nhập")


class SearchForm(FlaskForm):
    name = StringField("Tên hồ", validators=[Optional()])
    district_id = SelectField("Quận/huyện", coerce=int, validators=[Optional()])
    address = StringField("Địa chỉ", validators=[Optional()])
    fishing_type = StringField("Loại hình câu", validators=[Optional()])
    min_price = FloatField("Giá từ", validators=[Optional(), NumberRange(min=0)])
    max_price = FloatField("Giá đến", validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField("Tìm kiếm")


class PondForm(FlaskForm):
    name = StringField("Tên hồ câu", validators=[DataRequired(), Length(max=150)])
    district_id = SelectField("Quận/huyện", coerce=int, validators=[DataRequired()])
    address = StringField("Địa chỉ", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Mô tả", validators=[Optional(), Length(max=2000)])
    phone = StringField("Số điện thoại", validators=[Optional(), Length(max=20)])
    open_time = StringField(
        "Giờ mở cửa",
        validators=[
            DataRequired(), Length(max=20),
            Regexp(TIME_RE, message="Định dạng giờ phải là HH:MM (VD: 05:30)."),
        ],
    )
    close_time = StringField(
        "Giờ đóng cửa",
        validators=[
            DataRequired(), Length(max=20),
            Regexp(TIME_RE, message="Định dạng giờ phải là HH:MM (VD: 21:00)."),
        ],
    )
    fishing_type = StringField("Loại hình câu", validators=[DataRequired(), Length(max=120)])
    price_per_slot = FloatField("Giá vé", validators=[DataRequired(), NumberRange(min=0)])
    total_slots = IntegerField("Tổng số chỗ", validators=[DataRequired(), NumberRange(min=1)])
    available_slots = IntegerField("Chỗ còn trống", validators=[DataRequired(), NumberRange(min=0)])
    featured = BooleanField("Hồ nổi bật")
    image_url = StringField("Ảnh đại diện (URL)", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Lưu")


class PondServiceForm(FlaskForm):
    service_ids = SelectMultipleField("Dịch vụ đi kèm", coerce=int, validators=[Optional()])
    submit = SubmitField("Cập nhật dịch vụ")


class PondFishTypeForm(FlaskForm):
    pond_id = SelectField("Hồ câu", coerce=int, validators=[DataRequired()])
    fish_type_id = SelectField("Loại cá", coerce=int, validators=[DataRequired()])
    quantity_estimate = IntegerField("Số lượng ước tính", validators=[DataRequired(), NumberRange(min=0)])
    note = StringField("Ghi chú", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Lưu loại cá")


class FishingActivityForm(FlaskForm):
    pond_id = SelectField("Hồ câu", coerce=int, validators=[DataRequired()])
    fish_type_id = SelectField("Loại cá", coerce=int, validators=[DataRequired()])
    customer_name = StringField("Tên khách", validators=[DataRequired(), Length(max=120)])
    activity_date = DateField("Ngày hoạt động", validators=[DataRequired()], default=date.today)
    session = SelectField("Khung giờ", coerce=str, validators=[DataRequired()])
    catch_weight = FloatField("Khối lượng cá câu được (kg)", validators=[Optional(), NumberRange(min=0)])
    note = TextAreaField("Ghi chú", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Lưu hoạt động")


class BookingForm(FlaskForm):
    booking_date = DateField("Ngày đặt", validators=[DataRequired()], default=date.today)
    session = SelectField("Khung giờ", coerce=str, validators=[DataRequired()])
    slot_count = IntegerField("Số lượng chỗ", validators=[DataRequired(), NumberRange(min=1)])
    note = TextAreaField("Ghi chú", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Đặt chỗ")

    def validate_booking_date(self, field):
        if field.data < date.today():
            raise ValidationError("Ngày đặt phải từ hôm nay trở đi.")


class ReviewForm(FlaskForm):
    booking_id = SelectField("Đơn đặt (tuỳ chọn)", coerce=int, validators=[])
    rating = IntegerField(
        "Điểm đánh giá (1-5)",
        validators=[
            DataRequired(message="Vui lòng chọn điểm đánh giá."),
            NumberRange(min=1, max=5, message="Điểm phải từ 1 đến 5."),
        ],
    )
    comment = TextAreaField(
        "Nhận xét",
        validators=[Optional(), Length(max=1000)],
    )
    submit = SubmitField("Gửi đánh giá")
