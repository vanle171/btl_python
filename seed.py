from datetime import date, time, timedelta
import os

from extensions import db
from models import (
    Booking,
    District,
    FishType,
    FishingPond,
    FishingActivity,
    Image,
    Payment,
    PondFishType,
    PondService,
    Review,
    Role,
    Service,
    User,
)

ADMIN_PASSWORD    = os.environ.get("SEED_ADMIN_PASSWORD",    "")
OWNER_PASSWORD    = os.environ.get("SEED_OWNER_PASSWORD",    "")
CUSTOMER_PASSWORD = os.environ.get("SEED_CUSTOMER_PASSWORD", "")


def _parse(s):
    parts = s.split(":")
    return time(int(parts[0]), int(parts[1]))


def _end_from_start(start_time_val, offset_hours=1):
    """add offset_hours to a time object, wrapping past midnight."""
    total_minutes = start_time_val.hour * 60 + start_time_val.minute + offset_hours * 60
    return time((total_minutes // 60) % 24, total_minutes % 60)


DISTRICTS = [
    "Ba Dinh",
    "Hoan Kiem",
    "Dong Da",
    "Hai Ba Trung",
    "Cau Giay",
    "Thanh Xuan",
    "Hoang Mai",
    "Long Bien",
    "Ha Dong",
    "Nam Tu Liem",
    "Bac Tu Liem",
    "Tay Ho",
    "Soc Son",
    "Dong Anh",
    "Gia Lam",
    "Thanh Tri",
    "Hoai Duc",
    "Quoc Oai",
    "Chuong My",
    "Thuong Tin",
    "Phu Xuyen",
    "Son Tay",
    "Ba Vi",
    "My Duc",
    "Ung Hoa",
]

DEFAULT_FISH_TYPES = [
    ("Cá trắm", "Loại cá phổ biến tại hồ câu dịch vụ"),
    ("Cá mè", "Loại cá số lượng lớn, dễ gặp"),
    ("Cá rô phi", "Phù hợp câu giải trí"),
    ("Cá chép", "Loại cá được nhiều khách ưa chuộng"),
]


def seed_data():
    if Role.query.first():
        #? backfill end_time for existing bookings
        for b in Booking.query.filter(Booking.end_time.is_(None)).all():
            st = b.start_time 
            b.end_time = _end_from_start(st)
        db.session.commit()
        #? backfill missing fish types on re-runs
        existing_fish_names = {item.name for item in FishType.query.all()}
        missing_fish_types = [
            FishType(name=name, description=description)
            for name, description in DEFAULT_FISH_TYPES
            if name not in existing_fish_names
        ]
        if missing_fish_types:
            db.session.add_all(missing_fish_types)
            db.session.commit()
        return

    roles = {
        "admin": Role(name="admin", description="Quan tri he thong"),
        "owner": Role(name="owner", description="Chu ho cau"),
        "customer": Role(name="customer", description="Nguoi dat cho"),
    }
    db.session.add_all(roles.values())

    districts = [District(name=name, description=f"Khu vuc {name}, Ha Noi") for name in DISTRICTS]
    db.session.add_all(districts)

    services = [
        Service(name="Cho thue can cau", description="Cho thue can cau theo gio", default_price=50000),
        Service(name="Ban moi cau", description="Moi cau va phu kien", default_price=30000),
        Service(name="Do an nuoc uong", description="Phuc vu tai cho", default_price=80000),
        Service(name="Bai gui xe", description="Giu xe may va o to", default_price=10000),
    ]
    db.session.add_all(services)
    fish_types = [FishType(name=name, description=description) for name, description in DEFAULT_FISH_TYPES]
    db.session.add_all(fish_types)
    db.session.flush()

    admin = User(
        full_name="Quan Tri Vien",
        username="admin",
        email="admin@hocauhn.vn",
        phone="0900000000",
        role=roles["admin"],
    )
    admin.set_password(ADMIN_PASSWORD)

    owner_1 = User(
        full_name="Nguyen Van Chu Ho",
        username="chuho1",
        email="owner1@hocauhn.vn",
        phone="0911111111",
        role=roles["owner"],
    )
    owner_1.set_password(OWNER_PASSWORD)

    owner_2 = User(
        full_name="Tran Thi Chu Ho",
        username="chuho2",
        email="owner2@hocauhn.vn",
        phone="0922222222",
        role=roles["owner"],
    )
    owner_2.set_password(OWNER_PASSWORD)

    customer = User(
        full_name="Le Van Nguoi Dung",
        username="khach1",
        email="user1@hocauhn.vn",
        phone="0933333333",
        role=roles["customer"],
    )
    customer.set_password(CUSTOMER_PASSWORD)

    db.session.add_all([admin, owner_1, owner_2, customer])
    db.session.flush()

    district_map = {district.name: district for district in districts}
    service_map = {service.name: service for service in services}
    fish_type_map = {fish_type.name: fish_type for fish_type in fish_types}

    ponds = [
        FishingPond(
            owner=owner_1,
            district=district_map["Cau Giay"],
            name="Ho Cau Yen Hoa",
            address="So 12 pho Yen Hoa, Cau Giay, Ha Noi",
            description="Khong gian thoang, phu hop cau giai tri cuoi tuan.",
            phone="0988000111",
            open_time="05:30",
            close_time="21:00",
            fishing_type="Cau don, cau dai",
            price_per_slot=150000,
            total_slots=40,
            available_slots=24,
            featured=True,
            approved=True,
            status="open",
        ),
        FishingPond(
            owner=owner_1,
            district=district_map["Long Bien"],
            name="Ho Cau Sinh Thai Long Bien",
            address="Ngo 88 Viet Hung, Long Bien, Ha Noi",
            description="Ho cau gia dinh co dich vu an uong va bai do xe.",
            phone="0988000222",
            open_time="06:00",
            close_time="22:00",
            fishing_type="Cau tu nhien",
            price_per_slot=180000,
            total_slots=55,
            available_slots=37,
            featured=True,
            approved=True,
            status="open",
        ),
        FishingPond(
            owner=owner_2,
            district=district_map["Ha Dong"],
            name="Ho Cau Ha Dong Riverside",
            address="Duong To Hieu, Ha Dong, Ha Noi",
            description="Co khu cau thi dau va khu danh cho nguoi moi.",
            phone="0988000333",
            open_time="05:00",
            close_time="20:30",
            fishing_type="Cau dai, cau thi dau",
            price_per_slot=200000,
            total_slots=60,
            available_slots=45,
            featured=False,
            approved=True,
            status="open",
        ),
        FishingPond(
            owner=owner_2,
            district=district_map["Soc Son"],
            name="Ho Cau Sinh Thai Soc Son",
            address="Xa Phu Minh, Soc Son, Ha Noi",
            description="Ho moi dang cho duyet, gan khu vui choi cuoi tuan.",
            phone="0988000444",
            open_time="06:30",
            close_time="18:30",
            fishing_type="Cau thu gian",
            price_per_slot=120000,
            total_slots=35,
            available_slots=35,
            featured=False,
            approved=False,
            status="open",
        ),
    ]
    db.session.add_all(ponds)
    db.session.flush()

    db.session.add_all(
        [
            Image(pond=ponds[0], image_url="https://images.unsplash.com/photo-1500375592092-40eb2168fd21", is_primary=True),
            Image(pond=ponds[1], image_url="https://images.unsplash.com/photo-1507525428034-b723cf961d3e", is_primary=True),
            Image(pond=ponds[2], image_url="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee", is_primary=True),
            Image(pond=ponds[3], image_url="https://images.unsplash.com/photo-1470770903676-69b98201ea1c", is_primary=True),
        ]
    )

    db.session.add_all(
        [
            PondService(pond=ponds[0], service=service_map["Cho thue can cau"], custom_price=50000),
            PondService(pond=ponds[0], service=service_map["Ban moi cau"], custom_price=30000),
            PondService(pond=ponds[0], service=service_map["Do an nuoc uong"], custom_price=100000),
            PondService(pond=ponds[1], service=service_map["Cho thue can cau"], custom_price=60000),
            PondService(pond=ponds[1], service=service_map["Bai gui xe"], custom_price=10000),
            PondService(pond=ponds[2], service=service_map["Ban moi cau"], custom_price=35000),
            PondService(pond=ponds[2], service=service_map["Do an nuoc uong"], custom_price=90000),
            PondService(pond=ponds[2], service=service_map["Bai gui xe"], custom_price=15000),
        ]
    )
    db.session.add_all(
        [
            PondFishType(pond=ponds[0], fish_type=fish_type_map["Cá trắm"], quantity_estimate=120),
            PondFishType(pond=ponds[0], fish_type=fish_type_map["Cá mè"], quantity_estimate=90),
            PondFishType(pond=ponds[1], fish_type=fish_type_map["Cá rô phi"], quantity_estimate=150),
            PondFishType(pond=ponds[1], fish_type=fish_type_map["Cá chép"], quantity_estimate=70),
            PondFishType(pond=ponds[2], fish_type=fish_type_map["Cá trắm"], quantity_estimate=110),
            PondFishType(pond=ponds[2], fish_type=fish_type_map["Cá rô phi"], quantity_estimate=130),
        ]
    )

    booking_start = time(7, 0)
    booking = Booking(
        user=customer,
        pond=ponds[0],
        booking_date=date.today() + timedelta(days=3),
        start_time=booking_start,
        end_time=time(8, 0),
        slot_count=2,
        unit_price=ponds[0].price_per_slot,
        total_price=ponds[0].price_per_slot * 2,
        status="confirmed",
    )
    db.session.add(booking)
    db.session.flush()

    db.session.add(
        Payment(
            booking=booking,
            amount=booking.total_price,
            method="cash",
            status="paid",
        )
    )
    db.session.add_all(
        [
            Review(user=customer, pond=ponds[0], rating=5, comment="Ho sach dep, nhan vien ho tro nhanh.", status="approved"),
            Review(user=customer, pond=ponds[1], rating=4, comment="Dich vu on, bai gui xe tien loi.", status="approved"),
        ]
    )
    db.session.add_all(
        [
            FishingActivity(
                pond=ponds[0],
                fish_type=fish_type_map["Cá trắm"],
                booking=booking,
                customer_name="Lê Văn Người Dùng",
                activity_date=date.today(),
                start_time=time(6, 30),
                end_time=time(10, 30),
                catch_weight=3.5,
                note="Buổi câu sáng cuối tuần.",
            ),
            FishingActivity(
                pond=ponds[0],
                fish_type=fish_type_map["Cá mè"],
                customer_name="Nguyễn Văn An",
                activity_date=date.today(),
                start_time=time(8, 0),
                end_time=time(11, 0),
                catch_weight=2.1,
                note="Khách quen của hồ.",
            ),
            FishingActivity(
                pond=ponds[2],
                fish_type=fish_type_map["Cá rô phi"],
                customer_name="Trần Minh Khoa",
                activity_date=date.today() - timedelta(days=1),
                start_time=time(7, 15),
                end_time=time(12, 15),
                catch_weight=4.2,
                note="Hoạt động nhóm 2 người.",
            ),
        ]
    )

    ponds[0].available_slots -= booking.slot_count
    db.session.commit()
