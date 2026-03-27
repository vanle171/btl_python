from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import BookingForm, SearchForm
from models import Booking, District, FishingPond, Payment, Review


main_bp = Blueprint("main", __name__)


@main_bp.app_context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}


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
    form = SearchForm(request.args, meta={"csrf": False})
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
    return render_template("main/pond_detail.html", pond=pond, reviews=reviews)


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

    form = BookingForm()
    if form.validate_on_submit():
        if form.slot_count.data > pond.available_slots:
            flash("Số chỗ trống không đủ.", "danger")
        else:
            total_price = pond.price_per_slot * form.slot_count.data
            booking = Booking(
                user=current_user,
                pond=pond,
                booking_date=form.booking_date.data,
                start_time=form.start_time.data,
                slot_count=form.slot_count.data,
                unit_price=pond.price_per_slot,
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
