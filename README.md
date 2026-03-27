# Website Quan Ly Ho Cau Ha Noi

Ung dung web full-stack xay dung bang Flask de quan ly ho cau tren dia ban thanh pho Ha Noi.

## Cau truc project

```text
BTL_python/
|-- app.py
|-- config.py
|-- extensions.py
|-- forms.py
|-- models.py
|-- seed.py
|-- requirements.txt
|-- routes/
|   |-- auth.py
|   |-- main.py
|   |-- owner.py
|   |-- admin.py
|-- templates/
|-- static/
|-- instance/
```

## Chuc nang

- Dang ky, dang nhap, phan quyen admin, chu ho, nguoi dung
- Tim kiem ho cau theo ten, dia chi, quan/huyen, loai cau, muc gia
- Dat cho, huy dat cho, xem lich su
- Chu ho quan ly ho cau, dich vu, doanh thu va xac nhan booking
- Admin thong ke, duyet ho cau, khoa/mo khoa tai khoan

## Tai khoan mau

- Admin: `admin` / `admin123`
- Chu ho: `chuho1` / `owner123`
- Nguoi dung: `khach1` / `user123`

## Huong dan chay

1. Tao moi truong ao:

```bash
python -m venv venv
```

2. Kich hoat:

```powershell
.\venv\Scripts\Activate.ps1
```

3. Cai thu vien:

```bash
pip install -r requirements.txt
```

4. Chay app:

```bash
python app.py
```

5. Truy cap:

```text
http://127.0.0.1:5000
```

## Ghi chu

- SQLite se duoc tao trong `instance/fishing_ponds.db`.
- Seed du lieu mau tu dong chay o lan khoi dong dau tien.
- Muon reset du lieu, xoa file database roi chay lai `python app.py`.
