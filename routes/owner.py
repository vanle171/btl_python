from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import extract, func

from extensions import db
from forms import FishingActivityForm, PondFishTypeForm, PondForm, PondServiceForm
from models import (
    Booking,
    District,
    FishType,
    FishingActivity,
    FishingPond,
    Image,
    PondFishType,
    PondService,
    Service,
)


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


def _owner_pond_choices():
    ponds = FishingPond.query.filter_by(owner_id=current_user.id).order_by(FishingPond.name.asc()).all()
    return [(pond.id, pond.name) for pond in ponds]


def _fish_type_choices():
    fish_types = FishType.query.order_by(FishType.name.asc()).all()
    return [(fish_type.id, fish_type.name) for fish_type in fish_types]


@owner_bp.route("/dashboard")
@owner_required
def dashboard():
    ponds = FishingPond.query.filter_by(owner_id=current_user.id).all()
    pond_ids = [pond.id for pond in ponds]
    bookings = Booking.query.filter(Booking.pond_id.in_(pond_ids)).all() if pond_ids else []
    activities = FishingActivity.query.filter(FishingActivity.pond_id.in_(pond_ids)).all() if pond_ids else []
    pond_fish_rows = PondFishType.query.filter(PondFishType.pond_id.in_(pond_ids)).all() if pond_ids else []

    confirmed_bookings = [booking for booking in bookings if booking.status == "confirmed"]
    pending_bookings = [booking for booking in bookings if booking.status == "pending"]
    total_revenue = sum(booking.total_price for booking in confirmed_bookings)
    total_fish_types = len({row.fish_type_id for row in pond_fish_rows})

    fish_type_summary = {}
    for row in pond_fish_rows:
        fish_type_summary[row.fish_type.name] = fish_type_summary.get(row.fish_type.name, 0) + row.quantity_estimate

    pond_activity_summary = [
        {"pond_name": pond.name, "activity_count": len(pond.fishing_activities)}
        for pond in ponds
    ]

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
        activities=activities,
        pending_bookings=pending_bookings,
        total_revenue=total_revenue,
        total_fish_types=total_fish_types,
        fish_type_summary=fish_type_summary,
        pond_activity_summary=pond_activity_summary,
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


@owner_bp.route("/fish-types")
@owner_required
def fish_types():
    pond_ids = [pond.id for pond in FishingPond.query.filter_by(owner_id=current_user.id).all()]
    rows = (
        PondFishType.query.filter(PondFishType.pond_id.in_(pond_ids))
        .order_by(PondFishType.created_at.desc())
        .all()
        if pond_ids
        else []
    )
    return render_template("owner/fish_types.html", rows=rows)


@owner_bp.route("/fish-types/create", methods=["GET", "POST"])
@owner_required
def create_fish_type():
    form = PondFishTypeForm()
    form.pond_id.choices = _owner_pond_choices()
    form.fish_type_id.choices = _fish_type_choices()
    if not form.pond_id.choices:
        flash("Bạn cần tạo hồ câu trước khi thêm loại cá.", "warning")
        return redirect(url_for("owner.pond_management"))

    if form.validate_on_submit():
        pond = FishingPond.query.get_or_404(form.pond_id.data)
        if pond.owner_id != current_user.id:
            abort(403)
        existing_row = PondFishType.query.filter_by(
            pond_id=pond.id, fish_type_id=form.fish_type_id.data
        ).first()
        if existing_row:
            flash("Loại cá này đã tồn tại trong hồ câu đã chọn.", "warning")
        else:
            db.session.add(
                PondFishType(
                    pond_id=pond.id,
                    fish_type_id=form.fish_type_id.data,
                    quantity_estimate=form.quantity_estimate.data,
                    note=form.note.data,
                )
            )
            db.session.commit()
            flash("Đã thêm loại cá cho hồ câu.", "success")
            return redirect(url_for("owner.fish_types"))
    return render_template("owner/fish_type_form.html", form=form, title="Thêm loại cá")


@owner_bp.route("/fish-types/<int:row_id>/edit", methods=["GET", "POST"])
@owner_required
def edit_fish_type(row_id):
    row = PondFishType.query.get_or_404(row_id)
    if row.pond.owner_id != current_user.id:
        abort(403)

    form = PondFishTypeForm(obj=row)
    form.pond_id.choices = _owner_pond_choices()
    form.fish_type_id.choices = _fish_type_choices()
    if form.validate_on_submit():
        pond = FishingPond.query.get_or_404(form.pond_id.data)
        if pond.owner_id != current_user.id:
            abort(403)
        duplicate = (
            PondFishType.query.filter_by(pond_id=pond.id, fish_type_id=form.fish_type_id.data)
            .filter(PondFishType.id != row.id)
            .first()
        )
        if duplicate:
            flash("Loại cá này đã tồn tại trong hồ câu đã chọn.", "warning")
        else:
            row.pond_id = pond.id
            row.fish_type_id = form.fish_type_id.data
            row.quantity_estimate = form.quantity_estimate.data
            row.note = form.note.data
            db.session.commit()
            flash("Đã cập nhật loại cá.", "success")
            return redirect(url_for("owner.fish_types"))
    return render_template("owner/fish_type_form.html", form=form, title="Cập nhật loại cá")


@owner_bp.route("/fish-types/<int:row_id>/delete", methods=["POST"])
@owner_required
def delete_fish_type(row_id):
    row = PondFishType.query.get_or_404(row_id)
    if row.pond.owner_id != current_user.id:
        abort(403)
    db.session.delete(row)
    db.session.commit()
    flash("Đã xóa loại cá khỏi hồ câu.", "info")
    return redirect(url_for("owner.fish_types"))


@owner_bp.route("/activities")
@owner_required
def activities():
    pond_ids = [pond.id for pond in FishingPond.query.filter_by(owner_id=current_user.id).all()]
    items = (
        FishingActivity.query.filter(FishingActivity.pond_id.in_(pond_ids))
        .order_by(FishingActivity.activity_date.desc(), FishingActivity.created_at.desc())
        .all()
        if pond_ids
        else []
    )
    return render_template("owner/activities.html", activities=items)


@owner_bp.route("/activities/create", methods=["GET", "POST"])
@owner_required
def create_activity():
    form = FishingActivityForm()
    form.pond_id.choices = _owner_pond_choices()
    form.fish_type_id.choices = _fish_type_choices()
    if not form.pond_id.choices:
        flash("Bạn cần tạo hồ câu trước khi thêm hoạt động câu.", "warning")
        return redirect(url_for("owner.pond_management"))

    if form.validate_on_submit():
        pond = FishingPond.query.get_or_404(form.pond_id.data)
        if pond.owner_id != current_user.id:
            abort(403)
        db.session.add(
            FishingActivity(
                pond_id=pond.id,
                fish_type_id=form.fish_type_id.data,
                customer_name=form.customer_name.data,
                activity_date=form.activity_date.data,
                start_time=form.start_time.data,
                duration_hours=form.duration_hours.data,
                catch_weight=form.catch_weight.data or 0,
                note=form.note.data,
            )
        )
        db.session.commit()
        flash("Đã thêm hoạt động câu mới.", "success")
        return redirect(url_for("owner.activities"))
    return render_template("owner/activity_form.html", form=form, title="Thêm hoạt động câu")


@owner_bp.route("/activities/<int:activity_id>/edit", methods=["GET", "POST"])
@owner_required
def edit_activity(activity_id):
    activity = FishingActivity.query.get_or_404(activity_id)
    if activity.pond.owner_id != current_user.id:
        abort(403)

    form = FishingActivityForm(obj=activity)
    form.pond_id.choices = _owner_pond_choices()
    form.fish_type_id.choices = _fish_type_choices()
    if form.validate_on_submit():
        pond = FishingPond.query.get_or_404(form.pond_id.data)
        if pond.owner_id != current_user.id:
            abort(403)
        activity.pond_id = pond.id
        activity.fish_type_id = form.fish_type_id.data
        activity.customer_name = form.customer_name.data
        activity.activity_date = form.activity_date.data
        activity.start_time = form.start_time.data
        activity.duration_hours = form.duration_hours.data
        activity.catch_weight = form.catch_weight.data or 0
        activity.note = form.note.data
        db.session.commit()
        flash("Đã cập nhật hoạt động câu.", "success")
        return redirect(url_for("owner.activities"))
    return render_template("owner/activity_form.html", form=form, title="Cập nhật hoạt động câu")


@owner_bp.route("/activities/<int:activity_id>/delete", methods=["POST"])
@owner_required
def delete_activity(activity_id):
    activity = FishingActivity.query.get_or_404(activity_id)
    if activity.pond.owner_id != current_user.id:
        abort(403)
    db.session.delete(activity)
    db.session.commit()
    flash("Đã xóa hoạt động câu.", "info")
    return redirect(url_for("owner.activities"))


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
