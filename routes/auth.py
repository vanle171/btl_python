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
            flash("Vai tro khong hop le.", "danger")
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
        flash("Dang ky thanh cong. Ban co the dang nhap ngay.", "success")
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
            flash("Thong tin dang nhap khong chinh xac.", "danger")
        elif not user.is_active_account:
            flash("Tai khoan dang bi khoa.", "danger")
        else:
            login_user(user)
            flash("Dang nhap thanh cong.", "success")
            return redirect(next_page or url_for("main.index"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Ban da dang xuat.", "info")
    return redirect(url_for("main.index"))
