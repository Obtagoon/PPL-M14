# PPL-M14 Backend (Python FastAPI)

Backend REST API untuk pengelolaan komponen gaji per karyawan sesuai spesifikasi:
- **AC1**: Dasar perhitungan gaji (Gaji Pokok, Tunjangan, Potongan, Take-Home Pay).
- **AC4**: Penambahan beberapa tunjangan tetap atau potongan (mis. transport, makan, BPJS) yang tersimpan terpisah dengan nama dan nominalnya.

## Persyaratan
- Python >= 3.10 (termasuk modul bawaan `sqlite3`)
- Dependensi: `fastapi`, `uvicorn`, `pydantic`

## Instalasi Dependensi
```bash
pip install -r requirements.txt
```

## Menjalankan Server
Jalankan development server FastAPI (Uvicorn) pada port 8000:

```bash
# Dari root repositori
npm run backend

# Atau dari dalam folder backend
python -m uvicorn main:app --reload --port 8000
```

Server API akan aktif di `http://127.0.0.1:8000`.

## Dokumentasi Interaktif (Swagger UI & ReDoc)
FastAPI otomatis menyediakan dokumentasi interaktif yang dapat langsung diuji di browser:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

## Endpoints API

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/` atau `/api/health` | Health check & verifikasi API |
| `GET` | `/api/employees` | Mengambil seluruh daftar karyawan beserta komponen gaji |
| `GET` | `/api/employees/{id}/salary-components` | Mengambil komponen gaji karyawan tertentu beserta rincian tunjangan dan potongan |
| `POST` / `PUT` | `/api/employees/{id}/salary-components` | Menyimpan / memperbarui komponen gaji (Gaji Pokok, Tunjangan, Potongan) |
| `GET` | `/api/employees/{id}/salary-history` | Mengambil riwayat log perubahan komponen gaji karyawan |

## Format Payload Simpan Komponen Gaji (`POST`/`PUT`)
```json
{
  "basicSalary": 5000000,
  "fixedAllowance": 750000,
  "deduction": 100000,
  "effectiveFrom": "2026-11-01",
  "allowances": [
    { "id": "al-1", "name": "Tunjangan Transport", "amount": 500000 },
    { "id": "al-2", "name": "Tunjangan Makan", "amount": 250000 }
  ],
  "deductions": [
    { "id": "de-1", "name": "BPJS Ketenagakerjaan", "amount": 100000 }
  ]
}
```
