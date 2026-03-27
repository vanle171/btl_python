from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role", lazy=True)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    role = db.relationship("Role", back_populates="users")
    ponds = db.relationship("FishingPond", back_populates="owner", lazy=True)
    bookings = db.relationship("Booking", back_populates="user", lazy=True)
    reviews = db.relationship("Review", back_populates="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role and self.role.name == "admin"

    @property
    def is_owner(self):
        return self.role and self.role.name == "owner"

    @property
    def is_customer(self):
        return self.role and self.role.name == "customer"

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class District(TimestampMixin, db.Model):
    __tablename__ = "districts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    ponds = db.relationship("FishingPond", back_populates="district", lazy=True)


class FishingPond(TimestampMixin, db.Model):
    __tablename__ = "fishing_ponds"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    district_id = db.Column(db.Integer, db.ForeignKey("districts.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    phone = db.Column(db.String(20))
    open_time = db.Column(db.String(20), nullable=False)
    close_time = db.Column(db.String(20), nullable=False)
    fishing_type = db.Column(db.String(120), nullable=False)
    price_per_slot = db.Column(db.Float, nullable=False, default=0)
    total_slots = db.Column(db.Integer, nullable=False, default=0)
    available_slots = db.Column(db.Integer, nullable=False, default=0)
    featured = db.Column(db.Boolean, default=False, nullable=False)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(30), default="open", nullable=False)

    owner = db.relationship("User", back_populates="ponds")
    district = db.relationship("District", back_populates="ponds")
    services = db.relationship(
        "PondService", back_populates="pond", cascade="all, delete-orphan", lazy=True
    )
    bookings = db.relationship(
        "Booking", back_populates="pond", cascade="all, delete-orphan", lazy=True
    )
    reviews = db.relationship(
        "Review", back_populates="pond", cascade="all, delete-orphan", lazy=True
    )
    images = db.relationship(
        "Image", back_populates="pond", cascade="all, delete-orphan", lazy=True
    )

    @property
    def primary_image(self):
        primary = next((image for image in self.images if image.is_primary), None)
        if primary:
            return primary.image_url
        if self.images:
            return self.images[0].image_url
        return "https://images.unsplash.com/photo-1506744038136-46273834b3fb"

    @property
    def average_rating(self):
        approved_reviews = [item.rating for item in self.reviews if item.status == "approved"]
        if not approved_reviews:
            return 0
        return round(sum(approved_reviews) / len(approved_reviews), 1)


class Service(TimestampMixin, db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(255))
    default_price = db.Column(db.Float, default=0, nullable=False)

    ponds = db.relationship("PondService", back_populates="service", lazy=True)


class PondService(TimestampMixin, db.Model):
    __tablename__ = "pond_services"

    id = db.Column(db.Integer, primary_key=True)
    pond_id = db.Column(db.Integer, db.ForeignKey("fishing_ponds.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    custom_price = db.Column(db.Float, default=0, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    pond = db.relationship("FishingPond", back_populates="services")
    service = db.relationship("Service", back_populates="ponds")


class Booking(TimestampMixin, db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pond_id = db.Column(db.Integer, db.ForeignKey("fishing_ponds.id"), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    slot_count = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0)
    total_price = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(30), default="pending", nullable=False)
    note = db.Column(db.Text)
    confirmed_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="bookings")
    pond = db.relationship("FishingPond", back_populates="bookings")
    payment = db.relationship(
        "Payment", back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def can_cancel(self):
        return self.booking_date > date.today() and self.status in {"pending", "confirmed"}


class Payment(TimestampMixin, db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False, default=0)
    method = db.Column(db.String(50), default="cash", nullable=False)
    status = db.Column(db.String(30), default="unpaid", nullable=False)
    paid_at = db.Column(db.DateTime)
    transaction_code = db.Column(db.String(120))

    booking = db.relationship("Booking", back_populates="payment")


class Review(TimestampMixin, db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pond_id = db.Column(db.Integer, db.ForeignKey("fishing_ponds.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    status = db.Column(db.String(30), default="approved", nullable=False)

    user = db.relationship("User", back_populates="reviews")
    pond = db.relationship("FishingPond", back_populates="reviews")


class Image(TimestampMixin, db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    pond_id = db.Column(db.Integer, db.ForeignKey("fishing_ponds.id"), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)

    pond = db.relationship("FishingPond", back_populates="images")
