from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import extract, func

from extensions import db
from forms import PondForm, PondServiceForm
from models import Booking, District, FishingPond, Image, PondService, Service


owner_bp = Blueprint("owner", __name__, url_prefix="/owner")


def owner_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_owner:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper


def _district_choices():
    return [(district.id, district.name) for district in District.query.order_by(District.name.asc()).all()]


def _service_choices():
    return [
        (service.id, f"{service.name} - {service.default_price:,.0f} VND")
        for service in Service.query.order_by(Service.name.asc()).all()
    ]


@owner_bp.route("/dashboard")
@owner_required
def dashboard():
    ponds = FishingPond.query.filter_by(owner_id=current_user.id).all()
    pond_ids = [pond.id for pond in ponds]
    bookings = Booking.query.filter(Booking.pond_id.in_(pond_ids)).all() if pond_ids else []
    confirmed_bookings = [booking for booking in bookings if booking.status == "confirmed"]
    pending_bookings = [booking for booking in bookings if booking.status == "pending"]
    total_revenue = sum(booking.total_price for booking in confirmed_bookings)

    current_year = datetime.utcnow().year
    monthly_rows = (
        db.session.query(extract("month", Booking.booking_date), func.sum(Booking.total_price))
        .filter(
            Booking.pond_id.in_(pond_ids),
            Booking.status == "confirmed",
            extract("year", Booking.booking_date) == current_year,
        )
        .group_by(extract("month", Booking.booking_date))
        .all()
        if pond_ids
        else []
    )
    monthly_revenue = {int(month): float(total or 0) for month, total in monthly_rows}
    return render_template(
        "owner/dashboard.html",
        ponds=ponds,
        bookings=bookings,
        pending_bookings=pending_bookings,
        total_revenue=total_revenue,
        monthly_revenue=monthly_revenue,
    )


@owner_bp.route("/ponds")
@owner_required
def pond_management():
    ponds = FishingPond.query.filter_by(owner_id=current_user.id).order_by(FishingPond.created_at.desc()).all()
    return render_template("owner/pond_management.html", ponds=ponds)


@owner_bp.route("/ponds/create", methods=["GET", "POST"])
@owner_required
def create_pond():
    form = PondForm()
    form.district_id.choices = _district_choices()
    if form.validate_on_submit():
        pond = FishingPond(
            owner=current_user,
            district_id=form.district_id.data,
            name=form.name.data,
            address=form.address.data,
            description=form.description.data,
            phone=form.phone.data,
            open_time=form.open_time.data,
            close_time=form.close_time.data,
            fishing_type=form.fishing_type.data,
            price_per_slot=form.price_per_slot.data,
            total_slots=form.total_slots.data,
            available_slots=min(form.available_slots.data, form.total_slots.data),
            featured=form.featured.data,
            approved=False,
            status="open",
        )
        db.session.add(pond)
        db.session.flush()
        if form.image_url.data:
            db.session.add(Image(pond=pond, image_url=form.image_url.data, is_primary=True))
        db.session.commit()
        flash("Đã tạo hồ câu mới. Hệ thống sẽ cần duyệt trước khi hiển thị.", "success")
        return redirect(url_for("owner.pond_management"))
    return render_template("owner/pond_form.html", form=form, title="Thêm hồ câu")


@owner_bp.route("/ponds/<int:pond_id>/edit", methods=["GET", "POST"])
@owner_required
def edit_pond(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    if pond.owner_id != current_user.id:
        abort(403)

    form = PondForm(obj=pond)
    form.district_id.choices = _district_choices()
    if form.validate_on_submit():
        pond.district_id = form.district_id.data
        pond.name = form.name.data
        pond.address = form.address.data
        pond.description = form.description.data
        pond.phone = form.phone.data
        pond.open_time = form.open_time.data
        pond.close_time = form.close_time.data
        pond.fishing_type = form.fishing_type.data
        pond.price_per_slot = form.price_per_slot.data
        pond.total_slots = form.total_slots.data
        pond.available_slots = min(form.available_slots.data, form.total_slots.data)
        pond.featured = form.featured.data
        if form.image_url.data:
            primary = next((image for image in pond.images if image.is_primary), None)
            if primary:
                primary.image_url = form.image_url.data
            else:
                db.session.add(Image(pond=pond, image_url=form.image_url.data, is_primary=True))
        db.session.commit()
        flash("Cập nhật hồ câu thành công.", "success")
        return redirect(url_for("owner.pond_management"))

    primary = next((image for image in pond.images if image.is_primary), None)
    if primary:
        form.image_url.data = primary.image_url
    return render_template("owner/pond_form.html", form=form, title="Cập nhật hồ câu", pond=pond)


@owner_bp.route("/ponds/<int:pond_id>/delete", methods=["POST"])
@owner_required
def delete_pond(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    if pond.owner_id != current_user.id:
        abort(403)
    db.session.delete(pond)
    db.session.commit()
    flash("Đã xóa hồ câu.", "info")
    return redirect(url_for("owner.pond_management"))


@owner_bp.route("/ponds/<int:pond_id>/services", methods=["GET", "POST"])
@owner_required
def manage_services(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    if pond.owner_id != current_user.id:
        abort(403)

    form = PondServiceForm()
    form.service_ids.choices = _service_choices()
    if form.validate_on_submit():
        selected_ids = set(form.service_ids.data)
        current_ids = {item.service_id for item in pond.services}

        for item in list(pond.services):
            if item.service_id not in selected_ids:
                db.session.delete(item)

        for service_id in selected_ids - current_ids:
            service = Service.query.get(service_id)
            db.session.add(
                PondService(
                    pond=pond,
                    service=service,
                    custom_price=service.default_price,
                    is_available=True,
                )
            )
        db.session.commit()
        flash("Cập nhật dịch vụ đi kèm thành công.", "success")
        return redirect(url_for("owner.pond_management"))

    form.service_ids.data = [item.service_id for item in pond.services]
    return render_template("owner/service_form.html", form=form, pond=pond)


@owner_bp.route("/bookings")
@owner_required
def bookings():
    owner_bookings = (
        Booking.query.join(FishingPond)
        .filter(FishingPond.owner_id == current_user.id)
        .order_by(Booking.booking_date.desc(), Booking.created_at.desc())
        .all()
    )
    return render_template("owner/bookings.html", bookings=owner_bookings)


@owner_bp.route("/bookings/<int:booking_id>/confirm", methods=["POST"])
@owner_required
def confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.pond.owner_id != current_user.id:
        abort(403)
    booking.status = "confirmed"
    booking.confirmed_at = datetime.utcnow()
    if booking.payment:
        booking.payment.status = "paid"
        booking.payment.paid_at = datetime.utcnow()
    db.session.commit()
    flash("Đã xác nhận đơn đặt chỗ.", "success")
    return redirect(url_for("owner.bookings"))


@owner_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@owner_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.pond.owner_id != current_user.id:
        abort(403)
    if booking.status in {"pending", "confirmed"}:
        booking.pond.available_slots += booking.slot_count
    booking.status = "owner_cancelled"
    if booking.payment:
        booking.payment.status = "refunded"
    db.session.commit()
    flash("Đã hủy đơn đặt chỗ.", "warning")
    return redirect(url_for("owner.bookings"))
