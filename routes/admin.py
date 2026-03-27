from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models import Booking, District, FishingPond, Payment, User


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
    return render_template(
        "admin/dashboard.html",
        total_ponds=total_ponds,
        total_users=total_users,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        ponds_by_district=ponds_by_district,
        pending_ponds=pending_ponds,
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
    ponds = FishingPond.query.order_by(FishingPond.created_at.desc()).all()
    return render_template("admin/ponds.html", ponds=ponds)


@admin_bp.route("/ponds/<int:pond_id>/toggle-approval", methods=["POST"])
@admin_required
def toggle_approval(pond_id):
    pond = FishingPond.query.get_or_404(pond_id)
    pond.approved = not pond.approved
    db.session.commit()
    flash("Đã cập nhật trạng thái duyệt của hồ câu.", "success")
    return redirect(url_for("admin.ponds"))
