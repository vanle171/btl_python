from datetime import datetime, time, timezone
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

from config import Config
from extensions import db, login_manager
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.main import main_bp
from routes.owner import owner_bp
from seed import seed_data


def _migrate_booking_times():
    """convert legacy string start_time to Time, backfill end_time."""
    from models import Booking, FishingActivity

    def _parse_str(s):
        if s is None:
            return None
        parts = str(s).split(":")
        return time(int(parts[0]), int(parts[1]))

    def _end_from_start(st, offset_hours=1):
        total_min = st.hour * 60 + st.minute + offset_hours * 60
        return time((total_min // 60) % 24, total_min % 60)

    conn = db.engine.connect()
    try:
        conn.execute(db.text("ALTER TABLE bookings ADD COLUMN end_time TIME"))
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute(db.text("ALTER TABLE fishing_activities ADD COLUMN end_time TIME"))
        conn.commit()
    except Exception:
        pass

    #? add booking_id column if not present
    try:
        conn.execute(db.text("ALTER TABLE reviews ADD COLUMN booking_id INTEGER REFERENCES bookings(id)"))
        conn.commit()
    except Exception:
        pass

    bookings = Booking.query.all()
    for b in bookings:
        st = b.start_time
        if isinstance(st, str):
            st = _parse_str(st)
            b.start_time = st
        if b.end_time is None:
            b.end_time = _end_from_start(st)
        if isinstance(b.end_time, str):
            b.end_time = _parse_str(b.end_time)

    activities = FishingActivity.query.all()
    for a in activities:
        st = a.start_time
        if isinstance(st, str):
            st = _parse_str(st)
            a.start_time = st
        if a.end_time is None:
            dur = getattr(a, "duration_hours", 1) or 1
            a.end_time = _end_from_start(st, dur)
        if isinstance(a.end_time, str):
            a.end_time = _parse_str(a.end_time)

    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    CSRFProtect(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        return {"current_year": datetime.now(timezone.utc).year}

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    with app.app_context():
        db.create_all()
        _migrate_booking_times()
        seed_data()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
