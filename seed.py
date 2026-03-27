from datetime import date, timedelta

from extensions import db
from models import (
    Booking,
    District,
    FishingPond,
    Image,
    Payment,
    PondService,
    Review,
    Role,
    Service,
    User,
)


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


def seed_data():
    if Role.query.first():
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
    db.session.flush()

    admin = User(
        full_name="Quan Tri Vien",
        username="admin",
        email="admin@hocauhn.vn",
        phone="0900000000",
        role=roles["admin"],
    )
    admin.set_password("admin123")

    owner_1 = User(
        full_name="Nguyen Van Chu Ho",
        username="chuho1",
        email="owner1@hocauhn.vn",
        phone="0911111111",
        role=roles["owner"],
    )
    owner_1.set_password("owner123")

    owner_2 = User(
        full_name="Tran Thi Chu Ho",
        username="chuho2",
        email="owner2@hocauhn.vn",
        phone="0922222222",
        role=roles["owner"],
    )
    owner_2.set_password("owner123")

    customer = User(
        full_name="Le Van Nguoi Dung",
        username="khach1",
        email="user1@hocauhn.vn",
        phone="0933333333",
        role=roles["customer"],
    )
    customer.set_password("user123")

    db.session.add_all([admin, owner_1, owner_2, customer])
    db.session.flush()

    district_map = {district.name: district for district in districts}
    service_map = {service.name: service for service in services}

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

    booking = Booking(
        user=customer,
        pond=ponds[0],
        booking_date=date.today() + timedelta(days=3),
        start_time="07:00",
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
            Review(user=customer, pond=ponds[0], rating=5, comment="Ho sach dep, nhan vien ho tro nhanh."),
            Review(user=customer, pond=ponds[1], rating=4, comment="Dich vu on, bai gui xe tien loi."),
        ]
    )

    ponds[0].available_slots -= booking.slot_count
    db.session.commit()
