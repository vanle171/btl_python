from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import BookingForm, ReviewForm, SearchForm, generate_time_slots, parse_time
from models import Booking, District, FishingPond, Payment, Review


main_bp = Blueprint("main", __name__)


@main_bp.app_context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}


def non_customer_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(pond_id, *args, **kwargs):
        if current_user.is_owner or current_user.is_admin:
            flash("Tài khoản này không dùng để đặt chỗ như khách hàng.", "warning")
            return redirect(url_for("main.pond_detail", pond_id=pond_id))
        return view_func(pond_id, *args, **kwargs)

    return wrapper


@main_bp.route("/")
def index():
    featured_ponds = (
        FishingPond.query.filter_by(approved=True, featured=True)
        .order_by(FishingPond.created_at.desc())
        .limit(6)
        .all()
    )
    districts = District.query.order_by(District.name.asc()).all()
    featured_ponds_payload = [
        {
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
        for pond in featured_ponds
    ]
    return render_template(
        "main/index.html",
        featured_ponds=featured_ponds,
        featured_ponds_payload=featured_ponds_payload,
        districts=districts,
    )


@main_bp.route("/ponds")
def pond_list():
    form = SearchForm(request.args)
    form.district_id.choices = [(0, "Tất cả quận/huyện")] + [
        (district.id, district.name)
        for district in District.query.order_by(District.name.asc()).all()
    ]

    query = FishingPond.query.filter_by(approved=True)
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
    return render_template("main/pond_list.html", form=form, ponds=ponds)


@main_bp.route("/ponds/<int:pond_id>")
def pond_detail(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    if not pond.approved and (not current_user.is_authenticated or current_user.id != pond.owner_id):
        flash("Hồ câu này chưa được duyệt.", "warning")
        return redirect(url_for("main.pond_list"))

    reviews = (
        Review.query.filter_by(pond_id=pond.id, status="approved")
        .order_by(Review.created_at.desc())
        .all()
    )

    #? whether the current user already reviewed this pond
    already_reviewed = (
        current_user.is_authenticated
        and Review.query.filter_by(user_id=current_user.id, pond_id=pond.id).first() is not None
    )

    confirmed_bookings = []
    if current_user.is_authenticated and current_user.is_customer:
        confirmed_bookings = (
            Booking.query.filter_by(user_id=current_user.id, pond_id=pond.id, status="confirmed")
            .order_by(Booking.booking_date.desc())
            .all()
        )

    return render_template(
        "main/pond_detail.html",
        pond=pond,
        reviews=reviews,
        already_reviewed=already_reviewed,
        confirmed_bookings=confirmed_bookings,
    )


@main_bp.route("/ponds/<int:pond_id>/review", methods=["POST"])
@login_required
def create_review(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)

    if not current_user.is_customer:
        flash("Chỉ khách hàng mới có thể đánh giá.", "warning")
        return redirect(url_for("main.pond_detail", pond_id=pond_id))

    existing = Review.query.filter_by(user_id=current_user.id, pond_id=pond_id).first()
    if existing:
        flash("Bạn đã đánh giá hồ câu này rồi.", "info")
        return redirect(url_for("main.pond_detail", pond_id=pond_id))

    # Pre-fill booking choices for the select field
    confirmed_bookings = (
        Booking.query.filter_by(user_id=current_user.id, pond_id=pond_id, status="confirmed")
        .order_by(Booking.booking_date.desc())
        .all()
    )

    form = ReviewForm()
    form.booking_id.choices = [
        (0, "— Không chọn đơn cụ thể —")
    ] + [(b.id, f"Đơn ngày {b.booking_date.strftime('%d/%m/%Y')} ({b.time_display()})") for b in confirmed_bookings]

    if form.validate_on_submit():
        booking_id = form.booking_id.data
        if booking_id == 0:
            booking_id = None
        review = Review(
            user=current_user,
            pond=pond,
            booking_id=booking_id,
            rating=form.rating.data,
            comment=form.comment.data,
            status="pending",
        )
        db.session.add(review)
        db.session.commit()
        flash("Cảm ơn bạn! Đánh giá của bạn đã được gửi và đang chờ duyệt.", "success")
    else:
        for _, errors in form.errors.items():
            for e in errors:
                flash(e, "danger")

    return redirect(url_for("main.pond_detail", pond_id=pond_id))


@main_bp.route("/ponds/<int:pond_id>/book", methods=["GET", "POST"])
@non_customer_required
def create_booking(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    if not pond.approved:
        flash("Hồ câu chưa sẵn sàng nhận đặt chỗ.", "warning")
        return redirect(url_for("main.pond_detail", pond_id=pond_id))

    form = BookingForm()
    time_slots = generate_time_slots(pond.open_time, pond.close_time, interval_minutes=60)
    session_choices = [("", "— Chọn khung giờ —")] + [
        (start, label) for start, label in time_slots
    ]
    form.session.choices = session_choices

    if form.validate_on_submit():
        session_str = form.session.data
        start_str, end_str = session_str, None
        for s, l in time_slots:
            if s == session_str:
                end_str = l.split(" - ")[1]
                break

        start_t = parse_time(start_str)
        end_t = parse_time(end_str)

        if end_t <= start_t:
            flash("Giờ kết thúc phải sau giờ bắt đầu.", "danger")

        #? reject if there is a confirmed booking with overlapping time for this pond+date
        elif (
            Booking.query
            .filter(
                Booking.pond_id == pond_id,
                Booking.booking_date == form.booking_date.data,
                Booking.status == "confirmed",
                Booking.start_time < end_t,
                Booking.end_time > start_t,
            )
            .first()
        ):
            flash("Đã có đơn đặt khác xác nhận trùng giờ. Vui lòng chọn khung giờ khác.", "danger")
        else:
            #? lock the pond row to prevent concurrent bookings from racing on available_slots
            locked_pond = FishingPond.query.filter_by(id=pond_id).with_for_update().one()
            if form.slot_count.data > locked_pond.available_slots:
                flash("Số chỗ trống không đủ.", "danger")
            else:
                total_price = locked_pond.price_per_slot * form.slot_count.data
                booking = Booking(
                    user=current_user,
                    pond=locked_pond,
                    booking_date=form.booking_date.data,
                    start_time=start_t,
                    end_time=end_t,
                    slot_count=form.slot_count.data,
                    unit_price=locked_pond.price_per_slot,
                    total_price=total_price,
                    status="pending",
                    note=form.note.data,
                )
                payment = Payment(booking=booking, amount=total_price, method="cash", status="unpaid")
                locked_pond.available_slots -= form.slot_count.data
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
def cancel_my_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash("Bạn không có quyền thao tác với đơn này.", "danger")
        return redirect(url_for("main.booking_history"))

    if not booking.can_cancel:
        flash("Đơn đặt chỗ không còn hợp lệ để hủy.", "warning")
        return redirect(url_for("main.booking_history"))

    booking.status = "user_cancelled"
    booking.pond.available_slots += booking.slot_count
    if booking.payment:
        booking.payment.status = "refunded"
    db.session.commit()
    flash("Đã hủy đặt chỗ thành công.", "success")
    return redirect(url_for("main.booking_history"))
