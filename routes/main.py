from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import BookingForm, ReviewForm, SearchForm
from models import Booking, District, FishingPond, Payment, Promotion, Review


main_bp = Blueprint("main", __name__)

DISTRICT_COORDS = {
    "Ba Dinh": (21.0338, 105.8142),
    "Hoan Kiem": (21.0287, 105.8523),
    "Dong Da": (21.0180, 105.8290),
    "Hai Ba Trung": (21.0059, 105.8575),
    "Cau Giay": (21.0362, 105.7905),
    "Thanh Xuan": (20.9965, 105.8099),
    "Hoang Mai": (20.9744, 105.8640),
    "Long Bien": (21.0481, 105.8888),
    "Ha Dong": (20.9714, 105.7788),
    "Nam Tu Liem": (21.0126, 105.7658),
    "Bac Tu Liem": (21.0712, 105.7618),
    "Tay Ho": (21.0700, 105.8180),
    "Soc Son": (21.2608, 105.8483),
    "Dong Anh": (21.1368, 105.8486),
    "Gia Lam": (21.0289, 105.9350),
    "Thanh Tri": (20.9367, 105.8464),
    "Hoai Duc": (21.0332, 105.7075),
    "Quoc Oai": (20.9835, 105.6412),
    "Chuong My": (20.8834, 105.6647),
    "Thuong Tin": (20.8562, 105.8626),
    "Phu Xuyen": (20.7306, 105.9089),
    "Son Tay": (21.1383, 105.5061),
    "Ba Vi": (21.1936, 105.4230),
    "My Duc": (20.7248, 105.7173),
    "Ung Hoa": (20.7302, 105.7743),
}


@main_bp.app_context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}


def _public_pond_query():
    return FishingPond.query.filter_by(approved=True, status="open")


def _serialize_pond(pond):
    return {
        "id": pond.id,
        "name": pond.name,
        "district": pond.district.name,
        "address": pond.address,
        "description": pond.description or "Chưa có mô tả chi tiết.",
        "price_per_slot": pond.price_per_slot,
        "available_slots": pond.available_slots,
        "image": pond.primary_image,
        "detail_url": url_for("main.pond_detail", pond_id=pond.id),
    }


def _weekly_schedule(pond):
    schedule = []
    for offset in range(7):
        target_date = date.today() + timedelta(days=offset)
        day_bookings = [
            booking
            for booking in pond.bookings
            if booking.booking_date == target_date and booking.status in {"pending", "confirmed"}
        ]
        booked_slots = sum(item.slot_count for item in day_bookings)
        remain_slots = max(pond.total_slots - booked_slots, 0)
        schedule.append(
            {
                "date": target_date,
                "booked_slots": booked_slots,
                "remain_slots": remain_slots,
                "is_full": remain_slots == 0,
            }
        )
    return schedule


@main_bp.route("/")
def index():
    featured_ponds = (
        _public_pond_query()
        .filter_by(featured=True)
        .order_by(FishingPond.created_at.desc())
        .limit(6)
        .all()
    )
    top_ponds = sorted(
        _public_pond_query().all(),
        key=lambda pond: (
            len([item for item in pond.bookings if item.status == "confirmed"]),
            len(pond.fishing_activities),
            pond.average_rating,
        ),
        reverse=True,
    )[:5]
    districts = District.query.order_by(District.name.asc()).all()
    return render_template(
        "main/index.html",
        featured_ponds_payload=[_serialize_pond(pond) for pond in featured_ponds],
        top_ponds=top_ponds,
        districts=districts,
    )


@main_bp.route("/ponds")
def pond_list():
    form = SearchForm(request.args, meta={"csrf": False})
    form.district_id.choices = [(0, "Tất cả quận/huyện")] + [
        (district.id, district.name) for district in District.query.order_by(District.name.asc()).all()
    ]

    query = _public_pond_query()
    if form.name.data:
        query = query.filter(FishingPond.name.ilike(f"%{form.name.data.strip()}%"))
    if form.district_id.data:
        query = query.filter_by(district_id=form.district_id.data)
    if form.address.data:
        query = query.filter(FishingPond.address.ilike(f"%{form.address.data.strip()}%"))
    if form.fishing_type.data:
        query = query.filter(FishingPond.fishing_type.ilike(f"%{form.fishing_type.data.strip()}%"))
    if form.min_price.data is not None:
        query = query.filter(FishingPond.price_per_slot >= form.min_price.data)
    if form.max_price.data is not None:
        query = query.filter(FishingPond.price_per_slot <= form.max_price.data)

    ponds = query.order_by(FishingPond.featured.desc(), FishingPond.created_at.desc()).all()
    map_ponds = []
    for pond in ponds:
        coords = DISTRICT_COORDS.get(pond.district.name)
        if coords:
            map_ponds.append(
                {
                    "name": pond.name,
                    "district": pond.district.name,
                    "address": pond.address,
                    "price": pond.price_per_slot,
                    "detail_url": url_for("main.pond_detail", pond_id=pond.id),
                    "lat": coords[0],
                    "lng": coords[1],
                }
            )
    return render_template("main/pond_list.html", form=form, ponds=ponds, map_ponds=map_ponds)


@main_bp.route("/ponds/<int:pond_id>")
def pond_detail(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    can_view_hidden_pond = current_user.is_authenticated and current_user.id == pond.owner_id
    if not pond.approved and not can_view_hidden_pond:
        flash("Hồ câu này chưa được duyệt.", "warning")
        return redirect(url_for("main.pond_list"))
    if pond.status != "open" and not can_view_hidden_pond:
        flash("Hồ câu này đang ngừng hoạt động.", "warning")
        return redirect(url_for("main.pond_list"))

    reviews = (
        Review.query.filter_by(pond_id=pond.id, status="approved")
        .order_by(Review.created_at.desc())
        .all()
    )
    active_promotions = [
        promotion
        for promotion in pond.promotions
        if promotion.is_active and promotion.start_date <= date.today() <= promotion.end_date
    ]
    return render_template(
        "main/pond_detail.html",
        pond=pond,
        reviews=reviews,
        active_promotions=active_promotions,
        review_form=ReviewForm(),
        weekly_schedule=_weekly_schedule(pond),
    )


@main_bp.route("/ponds/<int:pond_id>/reviews", methods=["POST"])
@login_required
def submit_review(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    form = ReviewForm()
    if not current_user.is_customer:
        flash("Chỉ tài khoản người dùng mới có thể đánh giá hồ câu.", "warning")
        return redirect(url_for("main.pond_detail", pond_id=pond.id))
    if form.validate_on_submit():
        existing_review = Review.query.filter_by(user_id=current_user.id, pond_id=pond.id).first()
        if existing_review:
            existing_review.rating = form.rating.data
            existing_review.comment = form.comment.data
            existing_review.status = "approved"
            flash("Đã cập nhật đánh giá của bạn.", "success")
        else:
            db.session.add(
                Review(
                    user_id=current_user.id,
                    pond_id=pond.id,
                    rating=form.rating.data,
                    comment=form.comment.data,
                    status="approved",
                )
            )
            flash("Đã gửi đánh giá thành công.", "success")
        db.session.commit()
    else:
        flash("Vui lòng nhập đầy đủ nội dung đánh giá.", "warning")
    return redirect(url_for("main.pond_detail", pond_id=pond.id))


@main_bp.route("/ponds/<int:pond_id>/book", methods=["GET", "POST"])
@login_required
def create_booking(pond_id):
    if current_user.is_owner or current_user.is_admin:
        flash("Tài khoản này không dùng để đặt chỗ như khách hàng.", "warning")
        return redirect(url_for("main.pond_detail", pond_id=pond_id))

    pond = FishingPond.query.get_or_404(pond_id)
    if not pond.approved:
        flash("Hồ câu chưa sẵn sàng nhận đặt chỗ.", "warning")
        return redirect(url_for("main.pond_detail", pond_id=pond_id))
    if pond.status != "open":
        flash("Hồ câu tạm ngừng hoạt động nên chưa thể nhận đặt chỗ.", "warning")
        return redirect(url_for("main.pond_detail", pond_id=pond_id))

    form = BookingForm()
    if form.validate_on_submit():
        active_promotion = next(
            (
                promotion
                for promotion in pond.promotions
                if promotion.is_active and promotion.start_date <= form.booking_date.data <= promotion.end_date
            ),
            None,
        )
        unit_price = pond.price_per_slot
        if active_promotion:
            unit_price = pond.price_per_slot * (100 - active_promotion.discount_percent) / 100
        if form.slot_count.data > pond.available_slots:
            flash("Số chỗ trống không đủ.", "danger")
        else:
            total_price = unit_price * form.slot_count.data
            booking = Booking(
                user=current_user,
                pond=pond,
                booking_date=form.booking_date.data,
                start_time=form.start_time.data,
                slot_count=form.slot_count.data,
                unit_price=unit_price,
                total_price=total_price,
                status="pending",
                note=form.note.data,
            )
            payment = Payment(booking=booking, amount=total_price, method="cash", status="unpaid")
            pond.available_slots -= form.slot_count.data
            db.session.add_all([booking, payment])
            db.session.commit()
            flash("Đặt chỗ thành công. Chủ hồ sẽ xác nhận trong trang quản lý.", "success")
            return redirect(url_for("main.booking_history"))
    return render_template("main/booking.html", form=form, pond=pond)


@main_bp.route("/bookings")
@login_required
def booking_history():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template("main/booking_history.html", bookings=bookings)


@main_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash("Bạn không có quyền thao tác với đơn này.", "danger")
        return redirect(url_for("main.booking_history"))

    if not booking.can_cancel:
        flash("Đơn đặt chỗ không còn hợp lệ để hủy.", "warning")
        return redirect(url_for("main.booking_history"))

    booking.status = "cancelled"
    booking.pond.available_slots += booking.slot_count
    if booking.payment:
        booking.payment.status = "refunded"
    db.session.commit()
    flash("Đã hủy đặt chỗ thành công.", "success")
    return redirect(url_for("main.booking_history"))
