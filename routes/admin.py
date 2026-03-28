from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func

from extensions import db
from models import Booking, District, FishingPond, Payment, Review, User


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    total_ponds = FishingPond.query.count()
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(Payment.status == "paid").scalar() or 0
    ponds_by_district = (
        db.session.query(District.name, func.count(FishingPond.id))
        .outerjoin(FishingPond, FishingPond.district_id == District.id)
        .group_by(District.id)
        .order_by(func.count(FishingPond.id).desc(), District.name.asc())
        .all()
    )
    pending_ponds = FishingPond.query.filter_by(approved=False).order_by(FishingPond.created_at.desc()).all()
    recent_bookings = (
        Booking.query
        .order_by(Booking.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        total_ponds=total_ponds,
        total_users=total_users,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        ponds_by_district=ponds_by_district,
        pending_ponds=pending_ponds,
        recent_bookings=recent_bookings,
    )


@admin_bp.route("/users")
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Không thể khóa tài khoản đang đăng nhập.", "warning")
        return redirect(url_for("admin.users"))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    flash("Đã cập nhật trạng thái tài khoản.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/ponds")
@admin_required
def ponds():
    ponds = FishingPond.query.order_by(FishingPond.approved.asc(), FishingPond.created_at.desc()).all()
    return render_template("admin/ponds.html", ponds=ponds)


@admin_bp.route("/ponds/<int:pond_id>/toggle-approval", methods=["POST"])
@admin_required
def toggle_approval(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    pond.approved = not pond.approved
    db.session.commit()
    flash("Đã cập nhật trạng thái duyệt của hồ câu.", "success")
    return redirect(url_for("admin.ponds"))


@admin_bp.route("/bookings")
@admin_required
def bookings():
    all_bookings = (
        Booking.query.order_by(
            case((Booking.status == "pending", 0), else_=1),
            Booking.booking_date.desc(),
            Booking.created_at.desc(),
        ).all()
    )
    return render_template("admin/bookings.html", bookings=all_bookings)


@admin_bp.route("/bookings/<int:booking_id>/confirm", methods=["POST"])
@admin_required
def confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != "pending":
        flash("Đơn này không còn ở trạng thái chờ xác nhận.", "warning")
        return redirect(url_for("admin.bookings"))

    conflicting = (
        Booking.query
        .filter(
            Booking.id != booking.id,
            Booking.pond_id == booking.pond_id,
            Booking.booking_date == booking.booking_date,
            Booking.status == "pending",
            Booking.start_time < booking.end_time,
            Booking.end_time > booking.start_time,
        )
        .all()
    )
    for other in conflicting:
        other.status = "slot_conflict"
        if other.payment:
            other.payment.status = "refunded"
        other.pond.available_slots += other.slot_count

    booking.status = "confirmed"
    booking.confirmed_at = datetime.utcnow()
    if booking.payment:
        booking.payment.status = "paid"
        booking.payment.paid_at = datetime.utcnow()
    db.session.commit()

    msg = f"Đã duyệt đơn #{booking.id} cho khách {booking.user.username}."
    if conflicting:
        msg += f" {len(conflicting)} đơn trùng giờ đã bị từ chối và hoàn slot."
    flash(msg, "success")
    return redirect(url_for("admin.bookings"))


@admin_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@admin_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status in {"pending", "confirmed", "slot_conflict"}:
        booking.pond.available_slots += booking.slot_count
    booking.status = "admin_cancelled"
    if booking.payment:
        booking.payment.status = "refunded"
    db.session.commit()
    flash(f"Đã hủy đơn #{booking.id} của khách {booking.user.username}.", "warning")
    return redirect(url_for("admin.bookings"))


@admin_bp.route("/reviews")
@admin_required
def reviews():
    pending_reviews = Review.query.filter_by(status="pending").order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=pending_reviews)


@admin_bp.route("/reviews/<int:review_id>/approve", methods=["POST"])
@admin_required
def approve_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.status = "approved"
    db.session.commit()
    flash("Đã duyệt đánh giá.", "success")
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/reviews/<int:review_id>/reject", methods=["POST"])
@admin_required
def reject_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Đã từ chối đánh giá.", "info")
    return redirect(url_for("admin.reviews"))
