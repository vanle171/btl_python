# -*- coding: utf-8 -*-
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from forms import LoginForm, RegisterForm
from models import Role, User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        role = Role.query.filter_by(name=form.role.data).first()
        if not role:
            flash("Vai trò không hợp lệ.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=role,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Đăng ký thành công. Bạn có thể đăng nhập ngay.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    next_page = request.args.get("next")
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if not user or not user.check_password(form.password.data):
            flash("Thông tin đăng nhập không chính xác.", "danger")
        elif not user.is_active_account:
            flash("Tài khoản đang bị khóa.", "danger")
        else:
            login_user(user)
            flash("Đăng nhập thành công.", "success")
            return redirect(next_page or url_for("main.index"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("main.index"))
