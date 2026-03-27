from datetime import date

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
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from models import User


class RegisterForm(FlaskForm):
    full_name = StringField("Họ tên", validators=[DataRequired(), Length(max=120)])
    username = StringField("Tên đăng nhập", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField("Số điện thoại", validators=[Optional(), Length(max=20)])
    role = SelectField(
        "Loại tài khoản",
        choices=[("customer", "Người dùng"), ("owner", "Chủ hồ câu")],
        validators=[DataRequired()],
    )
    password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Xác nhận mật khẩu",
        validators=[DataRequired(), EqualTo("password")],
    )
    submit = SubmitField("Đăng ký")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Tên đăng nhập đã tồn tại.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Email đã tồn tại.")


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
    open_time = StringField("Giờ mở cửa", validators=[DataRequired(), Length(max=20)])
    close_time = StringField("Giờ đóng cửa", validators=[DataRequired(), Length(max=20)])
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
    start_time = StringField("Khung giờ", validators=[DataRequired(), Length(max=20)])
    duration_hours = IntegerField("Số giờ câu", validators=[DataRequired(), NumberRange(min=1)])
    catch_weight = FloatField("Khối lượng cá câu được (kg)", validators=[Optional(), NumberRange(min=0)])
    note = TextAreaField("Ghi chú", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Lưu hoạt động")


class BookingForm(FlaskForm):
    booking_date = DateField("Ngày đặt", validators=[DataRequired()], default=date.today)
    start_time = StringField("Khung giờ", validators=[DataRequired(), Length(max=20)])
    slot_count = IntegerField("Số lượng chỗ", validators=[DataRequired(), NumberRange(min=1)])
    note = TextAreaField("Ghi chú", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Đặt chỗ")

    def validate_booking_date(self, field):
        if field.data < date.today():
            raise ValidationError("Ngày đặt phải từ hôm nay trở đi.")
