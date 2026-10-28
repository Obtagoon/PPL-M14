"""
Router US2 - Perhitungan Gaji Berdasarkan Kehadiran
====================================================
Endpoint:
  POST /api/salary-calculation/hitung       - Hitung gaji berdasarkan rekap kehadiran
  GET  /api/salary-calculation/riwayat      - List riwayat hasil perhitungan
  GET  /api/salary-calculation/riwayat/{id} - Detail satu record hasil perhitungan
  GET  /api/salary-calculation/preview      - Preview perhitungan tanpa menyimpan

Sumber data:
  - Data Karyawan       : GET dari API M12 (external)
  - Data Rekap Kehadiran: GET dari API M13 (external)
  - Komponen Gaji (US1) : Database M14 sendiri (tabel salary_components)
  - Hasil Perhitungan   : Disimpan ke database M14 sendiri (tabel salary_calculations)

AC yang dicakup:
  AC1 - gaji = gaji_pokok + tunjangan - potongan (alpa & keterlambatan)
  AC2 - rekap kehadiran diambil dari M13 sesuai kontrak
  AC3 - potongan alpa dihitung per hari alpa
  AC4 - potongan keterlambatan dihitung per kejadian
  AC5 - rincian lengkap per karyawan tersimpan
  AC7 - gaji negatif ditandai untuk ditinjau (tidak dibulatkan)
"""

import os
import json
import secrets
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, status

from database import get_db_connection
from schemas_us2 import (
    DeductionRules,
    HasilPerhitunganKaryawan,
    HitungGajiRequest,
    HitungGajiResponse,
    KaryawanDilewati,
    KunciPeriodeRequest,
    ListSalaryCalculationResponse,
    PeriodeStatusResponse,
    RekapKehadiranM13,
    RincianGaji,
    SalaryCalculationRecord,
)

router = APIRouter(prefix="/api/salary-calculation", tags=["US2 - Salary Calculation"])

# ==============================================================================
# KONFIGURASI URL API EKSTERNAL (dari .env)
# ==============================================================================

M12_API_BASE = os.getenv("M12_API_BASE_URL", "")
M12_API_TOKEN = os.getenv("M12_API_TOKEN", "")
M12_LOGIN_EMAIL = os.getenv("M12_LOGIN_EMAIL", "")
M12_LOGIN_PASSWORD = os.getenv("M12_LOGIN_PASSWORD", "")
M13_API_BASE = os.getenv("M13_API_BASE_URL", "")

# Cache token M12 agar tidak login ulang setiap request
_m12_token_cache: dict = {"token": M12_API_TOKEN or None}


async def get_m12_token() -> str | None:
    """Ambil Bearer token M12 (dari .env atau auto-login)."""
    if _m12_token_cache["token"]:
        return _m12_token_cache["token"]

    env_token = os.getenv("M12_API_TOKEN")
    if env_token:
        _m12_token_cache["token"] = env_token
        return env_token

    if not M12_API_BASE or not M12_LOGIN_EMAIL:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{M12_API_BASE}/api/login",
                json={"email": M12_LOGIN_EMAIL, "password": M12_LOGIN_PASSWORD}
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("token") or data.get("data", {}).get("token")
            _m12_token_cache["token"] = token
            return token
    except Exception:
        return None


# ==============================================================================
# MOCK DATA — dipakai saat M12/M13 belum tersedia (URL kosong)
# ==============================================================================

MOCK_EMPLOYEES_M12 = {
    1: {"employee_id": 1, "name": "Andi Pratama",      "nik": "2026001", "department": "Operasional",         "position": "Staf Operasional"},
    2: {"employee_id": 2, "name": "Siti Rahma",        "nik": "2026002", "department": "Keuangan",            "position": "Staf Keuangan"},
    3: {"employee_id": 3, "name": "Budi Santoso",      "nik": "2026003", "department": "Sumber Daya Manusia", "position": "Staf HR"},
    4: {"employee_id": 4, "name": "Dewi Lestari",      "nik": "2026004", "department": "Operasional",         "position": "Supervisor"},
    5: {"employee_id": 5, "name": "Rizky Firmansyah",  "nik": "2026005", "department": "Teknologi Informasi", "position": "Staf IT"},
}

def _mock_rekap_m13(employee_id: int, bulan: int, tahun: int) -> dict:
    """Mock rekap kehadiran M13 — nilai berbeda per karyawan untuk variasi."""
    mock_map = {
        1: {"jumlah_hadir": 20, "jumlah_alpa": 1, "jumlah_keterlambatan": 3, "jumlah_izin": 1, "jumlah_sakit": 0},
        2: {"jumlah_hadir": 22, "jumlah_alpa": 0, "jumlah_keterlambatan": 1, "jumlah_izin": 0, "jumlah_sakit": 0},
        3: {"jumlah_hadir": 18, "jumlah_alpa": 2, "jumlah_keterlambatan": 5, "jumlah_izin": 2, "jumlah_sakit": 0},
        4: {"jumlah_hadir": 21, "jumlah_alpa": 0, "jumlah_keterlambatan": 0, "jumlah_izin": 0, "jumlah_sakit": 1},
        5: {"jumlah_hadir": 19, "jumlah_alpa": 3, "jumlah_keterlambatan": 2, "jumlah_izin": 0, "jumlah_sakit": 0},
    }
    base = mock_map.get(employee_id, {"jumlah_hadir": 20, "jumlah_alpa": 0, "jumlah_keterlambatan": 0, "jumlah_izin": 0, "jumlah_sakit": 0})
    return {
        "employee_id": employee_id,
        "periode_bulan": bulan,
        "periode_tahun": tahun,
        **base,
    }


# ==============================================================================
# HELPER: AMBIL DATA DARI API EKSTERNAL (AC2)
# ==============================================================================

async def fetch_employee_from_m12(employee_id: int) -> dict:
    """
    Ambil data karyawan dari API M12 dengan auto-login.
    Fallback ke mock jika M12 tidak tersedia atau data kosong.
    """
    if M12_API_BASE:
        token = await get_m12_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{M12_API_BASE}/api/employees/{employee_id}",
                    headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
                # Normalisasi field M12 → format internal M14
                emp_data = data.get("data", data) if isinstance(data, dict) else data
                return {
                    "employee_id": emp_data.get("id", employee_id),
                    "name": emp_data.get("name", emp_data.get("nama", "")),
                    "nik": emp_data.get("nik", ""),
                    "department": emp_data.get("department", emp_data.get("departemen", "")),
                    "position": emp_data.get("position", emp_data.get("jabatan", "")),
                }
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                _m12_token_cache["token"] = None
            # Jika 404 di M12 (misal M12 belum input data), lanjutkan ke fallback mock
            pass
        except httpx.HTTPError:
            pass

    # Fallback: mock data (saat M12 data masih kosong atau karyawan uji lokal)
    emp = MOCK_EMPLOYEES_M12.get(employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Karyawan dengan ID {employee_id} tidak ditemukan di M12 maupun data lokal."
        )
    return emp


async def fetch_rekap_from_m13(employee_id: int, bulan: int, tahun: int) -> RekapKehadiranM13:
    """
    Ambil rekap kehadiran dari API M13 sesuai kontrak (AC2).
    Format M13: GET /api/attendance/recap?month=YYYY-MM
    Response M13: { success, data: { rekap: [{karyawan_id, hadir, terlambat, alpa, izin_sakit, cuti}] } }
    """
    if M13_API_BASE:
        try:
            month_str = f"{tahun}-{bulan:02d}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{M13_API_BASE}/api/attendance/recap",
                    params={"month": month_str}
                )
                resp.raise_for_status()
                body = resp.json()

                # Normalisasi response M13
                # Format: { "success": true, "data": { "rekap": [...], "periode": {...} } }
                rekap_list = []
                if isinstance(body, dict):
                    data_obj = body.get("data", body)
                    rekap_list = data_obj.get("rekap", [])

                # Cari data rekap untuk employee_id yang diminta
                karyawan_rekap = next(
                    (r for r in rekap_list if r.get("karyawan_id") == employee_id),
                    None
                )

                if karyawan_rekap:
                    return RekapKehadiranM13(
                        employee_id=employee_id,
                        periode_bulan=bulan,
                        periode_tahun=tahun,
                        jumlah_hadir=int(karyawan_rekap.get("hadir", 0)),
                        jumlah_alpa=int(karyawan_rekap.get("alpa", 0)),
                        jumlah_keterlambatan=int(karyawan_rekap.get("terlambat", 0)),
                        jumlah_izin=int(karyawan_rekap.get("izin_sakit", 0)),
                        jumlah_sakit=int(karyawan_rekap.get("cuti", 0)),
                    )
                else:
                    # Karyawan tidak ada di rekap M13 → anggap hadir semua
                    return RekapKehadiranM13(
                        employee_id=employee_id,
                        periode_bulan=bulan,
                        periode_tahun=tahun,
                        jumlah_hadir=22,
                        jumlah_alpa=0,
                        jumlah_keterlambatan=0,
                        jumlah_izin=0,
                        jumlah_sakit=0,
                    )

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"M13 error {exc.response.status_code}: {exc.response.text}"
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal menghubungi M13: {exc}"
            )

    # Fallback: mock data (saat M13 belum tersedia)
    return RekapKehadiranM13(**_mock_rekap_m13(employee_id, bulan, tahun))


# ==============================================================================
# HELPER: AMBIL KOMPONEN GAJI DARI DATABASE M14 (US1)
# ==============================================================================

def fetch_komponen_gaji_m14(conn, employee_id: int) -> Optional[dict]:
    """
    Ambil komponen gaji karyawan dari database M14 (hasil US1).
    Return None jika belum ada komponen gaji.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, basic_salary, fixed_allowance, deduction FROM salary_components WHERE employee_id = ?",
        (employee_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None

    sc_id = row["id"]
    cursor.execute(
        "SELECT type, amount FROM salary_items WHERE salary_component_id = ?",
        (sc_id,)
    )
    items = cursor.fetchall()

    total_allowances = sum(r["amount"] for r in items if r["type"] == "allowance")
    total_deductions = sum(r["amount"] for r in items if r["type"] == "deduction")

    return {
        "gaji_pokok": row["basic_salary"],
        "fixed_allowance": row["fixed_allowance"],
        "itemized_tunjangan": total_allowances,
        "fixed_deduction": row["deduction"],
        "itemized_potongan": total_deductions,
    }


# ==============================================================================
# HELPER: OTORISASI ROLE KEUANGAN / HR (U2-T12 / AC9)
# ==============================================================================

ALLOWED_ROLES_KEUANGAN_HR = {
    "admin hr",
    "hr",
    "keuangan",
    "finance",
    "divisi keuangan",
    "divisi hr",
    "divisi keuangan/hr",
}

def verify_keuangan_hr(
    x_user_role: Optional[str] = None,
    x_user_name: Optional[str] = None,
    authorization: Optional[str] = None,
) -> dict:
    """
    Otorisasi Role Keuangan / HR (U2-T12 / AC9).
    Memastikan pengguna memiliki role Keuangan atau HR sebelum mengakses fitur perhitungan gaji.
    """
    role = x_user_role
    if role is None:
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:].strip()
            role = "Employee" if token.lower() == "employee" else "Admin HR"
        else:
            role = None

    cleaned_role = (role or "").strip().lower()
    if cleaned_role not in ALLOWED_ROLES_KEUANGAN_HR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "forbidden",
                "code": 403,
                "message": "Akses Ditolak (HTTP 403): Fitur perhitungan gaji hanya dapat diakses oleh Divisi Keuangan/HR.",
                "currentRole": role or "tidak diketahui",
            }
        )

    return {"name": x_user_name or "Admin HR", "role": role}


# ==============================================================================
# CORE LOGIC: HITUNG GAJI (AC1, AC3, AC4, AC5, AC7)
# ==============================================================================

def hitung_gaji_karyawan(
    employee_data: dict,
    rekap: RekapKehadiranM13,
    komponen: dict,
    aturan: DeductionRules,
) -> HasilPerhitunganKaryawan:
    """
    Rumus inti perhitungan gaji (U2-T2):

    total_tunjangan = fixed_allowance + itemized_tunjangan
    potongan_tetap  = fixed_deduction + itemized_potongan
    potongan_alpa   = jumlah_alpa * potongan_per_hari_alpa          (AC3)
    potongan_tlb    = jumlah_keterlambatan * potongan_per_tlb       (AC4)
    total_potongan  = potongan_tetap + potongan_alpa + potongan_tlb
    gaji_bersih     = gaji_pokok + total_tunjangan - total_potongan (AC1)

    Jika gaji_bersih < 0 → is_negatif = True, ditandai untuk ditinjau (AC7)
    """
    gaji_pokok        = komponen["gaji_pokok"]
    total_tunjangan   = komponen["fixed_allowance"] + komponen["itemized_tunjangan"]
    potongan_tetap    = komponen["fixed_deduction"] + komponen["itemized_potongan"]

    # AC3: potongan alpa
    potongan_alpa     = rekap.jumlah_alpa * aturan.potongan_per_hari_alpa

    # AC4: potongan keterlambatan
    potongan_keterlambatan = rekap.jumlah_keterlambatan * aturan.potongan_per_keterlambatan

    total_potongan    = potongan_tetap + potongan_alpa + potongan_keterlambatan

    # AC1: rumus gaji bersih
    gaji_bersih       = gaji_pokok + total_tunjangan - total_potongan

    # AC7: tandai jika negatif, JANGAN dibulatkan ke 0
    is_negatif = gaji_bersih < 0
    catatan = (
        f"PERHATIAN: Gaji bersih bernilai negatif (Rp {gaji_bersih:,}). "
        "Mohon ditinjau oleh Admin HR sebelum diproses."
        if is_negatif else None
    )

    return HasilPerhitunganKaryawan(
        employee_id=employee_data["employee_id"],
        employee_name=employee_data["name"],
        nik=employee_data["nik"],
        department=employee_data["department"],
        position=employee_data["position"],
        periode_bulan=rekap.periode_bulan,
        periode_tahun=rekap.periode_tahun,
        rekap_kehadiran=rekap,
        rincian_gaji=RincianGaji(
            gaji_pokok=gaji_pokok,
            total_tunjangan=total_tunjangan,
            potongan_tetap=potongan_tetap,
            potongan_alpa=potongan_alpa,
            potongan_keterlambatan=potongan_keterlambatan,
            total_potongan=total_potongan,
            gaji_bersih=gaji_bersih,
        ),
        is_negatif=is_negatif,
        catatan=catatan,
    )


# ==============================================================================
# ENDPOINT 1: HITUNG GAJI (POST) — simpan ke DB
# ==============================================================================

@router.post(
    "/hitung",
    response_model=HitungGajiResponse,
    status_code=status.HTTP_200_OK,
    summary="Hitung gaji berdasarkan rekap kehadiran (AC1-AC7)",
    description="""
Menghitung gaji karyawan berdasarkan:
- Data karyawan dari API M12
- Rekap kehadiran dari API M13 (jumlah alpa & keterlambatan)
- Komponen gaji dari database M14 (US1)

Hasil disimpan ke tabel `salary_calculations` untuk audit trail.
Memerlukan role **Admin HR** (header `X-User-Role: Admin HR`).
    """,
)
async def hitung_gaji(
    payload: HitungGajiRequest,
    x_user_role: Optional[str] = Header(None),
    x_user_name: Optional[str] = Header("Rani K. (Admin HR)"),
    authorization: Optional[str] = Header(None),
):
    # Otorisasi role Keuangan/HR (U2-T12 / AC9)
    admin_user = verify_keuangan_hr(x_user_role, x_user_name, authorization)

    aturan = payload.aturan_potongan or DeductionRules()
    hasil_list: List[HasilPerhitunganKaryawan] = []
    dilewati_list: List[KaryawanDilewati] = []
    peringatan_list: List[str] = []

    conn = get_db_connection()
    try:
        # AC8: Cek apakah periode penggajian sudah dikunci
        locked, lock_info = is_period_locked(conn, payload.periode_bulan, payload.periode_tahun)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "code": 400,
                    "message": f"Periode penggajian {payload.periode_bulan}/{payload.periode_tahun} sudah dikunci (final). Perhitungan ulang tidak dapat dilakukan.",
                    "locked_at": lock_info.get("locked_at") if lock_info else None,
                    "locked_by": lock_info.get("locked_by") if lock_info else None,
                }
            )

        for emp_id in payload.employee_ids:
            # AC2: ambil data karyawan dari M12
            emp_data = await fetch_employee_from_m12(emp_id)

            # AC6: Karyawan tanpa komponen gaji dilewati dan ditandai dengan peringatan
            komponen = fetch_komponen_gaji_m14(conn, emp_id)
            if not komponen:
                emp_name = emp_data.get("name", f"Karyawan ID {emp_id}")
                dilewati_list.append(KaryawanDilewati(
                    employee_id=emp_id,
                    employee_name=emp_name,
                    alasan="Komponen gaji belum diatur di US1"
                ))
                peringatan_list.append(
                    f"Karyawan {emp_name} (ID: {emp_id}) dilewati karena belum memiliki data komponen gaji (US1)."
                )
                continue

            # AC2: ambil rekap kehadiran dari M13
            rekap = await fetch_rekap_from_m13(emp_id, payload.periode_bulan, payload.periode_tahun)

            # AC1, AC3, AC4, AC5, AC7: hitung gaji
            hasil = hitung_gaji_karyawan(emp_data, rekap, komponen, aturan)
            hasil_list.append(hasil)

            # Simpan ke DB M14 (U2-T5)
            _save_calculation(conn, hasil, x_user_name or "Admin HR")

        conn.commit()
    finally:
        conn.close()

    return HitungGajiResponse(
        periode_bulan=payload.periode_bulan,
        periode_tahun=payload.periode_tahun,
        jumlah_karyawan=len(hasil_list),
        hasil=hasil_list,
        karyawan_dilewati=dilewati_list,
        peringatan=peringatan_list,
        aturan_potongan_digunakan=aturan,
    )


# ==============================================================================
# ENDPOINT 2: PREVIEW PERHITUNGAN (GET) — tidak simpan ke DB
# ==============================================================================

@router.get(
    "/preview",
    response_model=HitungGajiResponse,
    summary="Preview perhitungan gaji tanpa menyimpan",
    description="Hitung gaji karyawan untuk preview. Tidak disimpan ke database.",
)
async def preview_hitung_gaji(
    employee_ids: str = Query(..., description="ID karyawan dipisah koma, contoh: 1,2,3"),
    periode_bulan: int = Query(..., ge=1, le=12),
    periode_tahun: int = Query(..., ge=2000),
    potongan_alpa: int = Query(default=100000, ge=0, description="Nominal potongan per hari alpa"),
    potongan_keterlambatan: int = Query(default=25000, ge=0, description="Nominal potongan per keterlambatan"),
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    # Otorisasi role Keuangan/HR (U2-T12 / AC9)
    verify_keuangan_hr(x_user_role, authorization=authorization)

    try:
        ids = [int(i.strip()) for i in employee_ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Format employee_ids tidak valid. Gunakan angka dipisah koma, contoh: 1,2,3")

    aturan = DeductionRules(
        potongan_per_hari_alpa=potongan_alpa,
        potongan_per_keterlambatan=potongan_keterlambatan,
    )
    hasil_list: List[HasilPerhitunganKaryawan] = []
    dilewati_list: List[KaryawanDilewati] = []
    peringatan_list: List[str] = []

    conn = get_db_connection()
    try:
        for emp_id in ids:
            emp_data = await fetch_employee_from_m12(emp_id)

            # AC6: Karyawan tanpa komponen gaji dilewati dan ditandai dengan peringatan
            komponen = fetch_komponen_gaji_m14(conn, emp_id)
            if not komponen:
                emp_name = emp_data.get("name", f"Karyawan ID {emp_id}")
                dilewati_list.append(KaryawanDilewati(
                    employee_id=emp_id,
                    employee_name=emp_name,
                    alasan="Komponen gaji belum diatur di US1"
                ))
                peringatan_list.append(
                    f"Karyawan {emp_name} (ID: {emp_id}) dilewati karena belum memiliki data komponen gaji (US1)."
                )
                continue

            rekap = await fetch_rekap_from_m13(emp_id, periode_bulan, periode_tahun)
            hasil = hitung_gaji_karyawan(emp_data, rekap, komponen, aturan)
            hasil_list.append(hasil)
    finally:
        conn.close()

    return HitungGajiResponse(
        periode_bulan=periode_bulan,
        periode_tahun=periode_tahun,
        jumlah_karyawan=len(hasil_list),
        hasil=hasil_list,
        karyawan_dilewati=dilewati_list,
        peringatan=peringatan_list,
        aturan_potongan_digunakan=aturan,
    )


# ==============================================================================
# ENDPOINT 3: LIST RIWAYAT HASIL PERHITUNGAN (GET)
# ==============================================================================

@router.get(
    "/riwayat",
    response_model=ListSalaryCalculationResponse,
    summary="Daftar riwayat hasil perhitungan gaji",
)
def get_riwayat(
    periode_bulan: Optional[int] = Query(None, ge=1, le=12),
    periode_tahun: Optional[int] = Query(None, ge=2000),
    employee_id: Optional[int] = Query(None),
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    # Otorisasi role Keuangan/HR (U2-T12 / AC9)
    verify_keuangan_hr(x_user_role, authorization=authorization)

    conn = get_db_connection()
    try:
        query = "SELECT * FROM salary_calculations WHERE 1=1"
        params = []
        if periode_bulan:
            query += " AND periode_bulan = ?"
            params.append(periode_bulan)
        if periode_tahun:
            query += " AND periode_tahun = ?"
            params.append(periode_tahun)
        if employee_id:
            query += " AND employee_id = ?"
            params.append(employee_id)
        query += " ORDER BY dihitung_pada DESC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        records = [SalaryCalculationRecord(**dict(r)) for r in rows]
        return ListSalaryCalculationResponse(data=records, total=len(records))
    finally:
        conn.close()


# ==============================================================================
# ENDPOINT 4: DETAIL SATU RECORD HASIL PERHITUNGAN (GET)
# ==============================================================================

@router.get(
    "/riwayat/{record_id}",
    response_model=SalaryCalculationRecord,
    summary="Detail satu record hasil perhitungan gaji",
)
def get_riwayat_detail(
    record_id: str,
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    # Otorisasi role Keuangan/HR (U2-T12 / AC9)
    verify_keuangan_hr(x_user_role, authorization=authorization)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salary_calculations WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record perhitungan dengan ID '{record_id}' tidak ditemukan."
            )
        return SalaryCalculationRecord(**dict(row))
    finally:
        conn.close()


# ==============================================================================
# HELPER INTERNAL: CEK STATUS PENGUNCIAN PERIODE & UPSERT (U2-T10 / AC8)
# ==============================================================================

def is_period_locked(conn, periode_bulan: int, periode_tahun: int) -> tuple[bool, Optional[dict]]:
    """
    Cek apakah periode penggajian sudah dikunci (AC8).
    Return (is_locked: bool, info: dict atau None)
    """
    period_id = f"{periode_tahun}-{periode_bulan:02d}"
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, periode_bulan, periode_tahun, is_locked, locked_at, locked_by
        FROM payroll_periods
        WHERE id = ?
    """, (period_id,))
    row = cursor.fetchone()
    if not row:
        return False, None

    is_locked = bool(row["is_locked"])
    return is_locked, dict(row)


def _save_calculation(conn, hasil: HasilPerhitunganKaryawan, dihitung_oleh: str):
    """
    Simpan atau perbarui (upsert) hasil perhitungan ke tabel salary_calculations.
    AC8: Jika sudah pernah dihitung sebelumnya untuk periode ini, perbarui datanya.
    """
    now = datetime.now().isoformat()
    r = hasil.rincian_gaji
    cursor = conn.cursor()

    # Cek apakah record perhitungan untuk karyawan & periode ini sudah ada
    cursor.execute("""
        SELECT id FROM salary_calculations 
        WHERE employee_id = ? AND periode_bulan = ? AND periode_tahun = ?
    """, (hasil.employee_id, hasil.periode_bulan, hasil.periode_tahun))
    existing = cursor.fetchone()

    if existing:
        # AC8: Perbarui record yang ada dengan hasil perhitungan terbaru
        record_id = existing["id"]
        cursor.execute("""
            UPDATE salary_calculations
            SET employee_name = ?, gaji_pokok = ?, total_tunjangan = ?,
                potongan_tetap = ?, potongan_alpa = ?, potongan_keterlambatan = ?,
                total_potongan = ?, gaji_bersih = ?, is_negatif = ?,
                jumlah_alpa = ?, jumlah_keterlambatan = ?,
                dihitung_oleh = ?, dihitung_pada = ?
            WHERE id = ?
        """, (
            hasil.employee_name,
            r.gaji_pokok,
            r.total_tunjangan,
            r.potongan_tetap,
            r.potongan_alpa,
            r.potongan_keterlambatan,
            r.total_potongan,
            r.gaji_bersih,
            hasil.is_negatif,
            hasil.rekap_kehadiran.jumlah_alpa,
            hasil.rekap_kehadiran.jumlah_keterlambatan,
            dihitung_oleh,
            now,
            record_id,
        ))
    else:
        # Insert baru jika belum ada
        record_id = f"calc-{secrets.token_hex(6)}"
        cursor.execute("""
            INSERT INTO salary_calculations (
                id, employee_id, employee_name,
                periode_bulan, periode_tahun,
                gaji_pokok, total_tunjangan, potongan_tetap,
                potongan_alpa, potongan_keterlambatan, total_potongan, gaji_bersih,
                is_negatif, jumlah_alpa, jumlah_keterlambatan,
                dihitung_oleh, dihitung_pada
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id,
            hasil.employee_id,
            hasil.employee_name,
            hasil.periode_bulan,
            hasil.periode_tahun,
            r.gaji_pokok,
            r.total_tunjangan,
            r.potongan_tetap,
            r.potongan_alpa,
            r.potongan_keterlambatan,
            r.total_potongan,
            r.gaji_bersih,
            hasil.is_negatif,
            hasil.rekap_kehadiran.jumlah_alpa,
            hasil.rekap_kehadiran.jumlah_keterlambatan,
            dihitung_oleh,
            now,
        ))


# ==============================================================================
# ENDPOINT 5 & 6: KUNCI / BUKA KUNCI PERIODE (U2-T10 / AC8)
# ==============================================================================

@router.post(
    "/periode/kunci",
    summary="Kunci periode penggajian (Finalisasi)",
    description="Mengunci periode penggajian agar tidak dapat dihitung ulang atau diubah lagi (AC8)."
)
def kunci_periode(
    payload: KunciPeriodeRequest,
    x_user_role: Optional[str] = Header(None),
    x_user_name: Optional[str] = Header("Admin HR"),
    authorization: Optional[str] = Header(None),
):
    # Otorisasi role Keuangan/HR (U2-T12 / AC9)
    admin_user = verify_keuangan_hr(x_user_role, x_user_name, authorization)

    period_id = f"{payload.periode_tahun}-{payload.periode_bulan:02d}"
    now = datetime.now().isoformat()
    admin_name = admin_user.get("name", "Admin HR")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, is_locked FROM payroll_periods WHERE id = ?", (period_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE payroll_periods
                SET is_locked = ?, locked_at = ?, locked_by = ?
                WHERE id = ?
            """, (True, now, admin_name, period_id))
        else:
            cursor.execute("""
                INSERT INTO payroll_periods (id, periode_bulan, periode_tahun, is_locked, locked_at, locked_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (period_id, payload.periode_bulan, payload.periode_tahun, True, now, admin_name, now))

        conn.commit()
        return {
            "success": True,
            "message": f"Periode penggajian {payload.periode_bulan}/{payload.periode_tahun} berhasil dikunci.",
            "is_locked": True,
            "locked_at": now,
            "locked_by": admin_name,
        }
    finally:
        conn.close()


@router.post(
    "/periode/buka-kunci",
    summary="Buka kunci periode penggajian",
    description="Membuka kunci periode penggajian agar admin dapat melakukan koreksi/hitung ulang (AC8)."
)
def buka_kunci_periode(
    payload: KunciPeriodeRequest,
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    # Otorisasi role Keuangan/HR (U2-T12 / AC9)
    verify_keuangan_hr(x_user_role, authorization=authorization)

    period_id = f"{payload.periode_tahun}-{payload.periode_bulan:02d}"

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM payroll_periods WHERE id = ?", (period_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE payroll_periods
                SET is_locked = ?, locked_at = NULL, locked_by = NULL
                WHERE id = ?
            """, (False, period_id))
            conn.commit()

        return {
            "success": True,
            "message": f"Kunci periode penggajian {payload.periode_bulan}/{payload.periode_tahun} berhasil dibuka.",
            "is_locked": False,
        }
    finally:
        conn.close()


@router.get(
    "/periode/status",
    response_model=PeriodeStatusResponse,
    summary="Cek status penguncian periode penggajian"
)
def get_periode_status(
    periode_bulan: int = Query(..., ge=1, le=12),
    periode_tahun: int = Query(..., ge=2000),
):
    conn = get_db_connection()
    try:
        locked, info = is_period_locked(conn, periode_bulan, periode_tahun)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM salary_calculations
            WHERE periode_bulan = ? AND periode_tahun = ?
        """, (periode_bulan, periode_tahun))
        count = cursor.fetchone()[0]

        return PeriodeStatusResponse(
            periode_bulan=periode_bulan,
            periode_tahun=periode_tahun,
            is_locked=locked,
            locked_at=info.get("locked_at") if info else None,
            locked_by=info.get("locked_by") if info else None,
            total_karyawan_terhitung=count,
        )
    finally:
        conn.close()
