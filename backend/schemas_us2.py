"""
Schemas untuk US2 - M14: Perhitungan Gaji Berdasarkan Kehadiran

Task coverage:
- U2-T1: Kontrak rekap kehadiran dari M13 (field: karyawan, periode, jumlah_alpa, jumlah_keterlambatan)
- U2-T2: Rumus & aturan potongan (alpa, keterlambatan, gaji negatif)
- U2-T3: Struktur hasil perhitungan per karyawan
- U2-T5: Model untuk tabel hasil perhitungan gaji

AC yang dicakup:
- AC1 : gaji = gaji_pokok + tunjangan - potongan (alpa & keterlambatan)
- AC2 : ambil rekap kehadiran dari M13 sesuai kontrak
- AC3 : potongan alpa dihitung sesuai aturan (per hari alpa)
- AC4 : potongan keterlambatan dihitung sesuai aturan
- AC5 : rincian: gaji_pokok, tunjangan, potongan_tetap, potongan_alpa, potongan_keterlambatan, gaji_bersih
- AC7 : jika gaji_bersih negatif, ditandai untuk ditinjau (bukan dibulatkan)
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# KONTRAK REKAP KEHADIRAN DARI M13 (U2-T1 / AC2)
# ==============================================================================

class RekapKehadiranM13(BaseModel):
    """
    Kontrak rekap kehadiran yang diterima dari API M13.
    Field ini disepakati bersama dengan kelompok M13.
    """
    employee_id: int = Field(..., description="ID karyawan (harus sama antara M13 dan M14)")
    periode_bulan: int = Field(..., ge=1, le=12, description="Bulan periode penggajian (1-12)")
    periode_tahun: int = Field(..., ge=2000, description="Tahun periode penggajian")
    jumlah_hadir: int = Field(default=0, ge=0, description="Jumlah hari hadir")
    jumlah_alpa: int = Field(default=0, ge=0, description="Jumlah hari alpa (tidak hadir tanpa keterangan)")
    jumlah_keterlambatan: int = Field(default=0, ge=0, description="Jumlah kejadian keterlambatan")
    jumlah_izin: Optional[int] = Field(default=0, ge=0, description="Jumlah hari izin resmi")
    jumlah_sakit: Optional[int] = Field(default=0, ge=0, description="Jumlah hari sakit")


# ==============================================================================
# ATURAN POTONGAN (U2-T2 / AC3, AC4)
# ==============================================================================

class DeductionRules(BaseModel):
    """
    Aturan potongan yang disepakati dengan divisi Keuangan/HR.
    Dapat dikonfigurasi per request atau menggunakan default sistem.
    """
    potongan_per_hari_alpa: int = Field(
        default=100000,
        ge=0,
        description="Nominal potongan per hari alpa (AC3). Default: Rp 100.000/hari"
    )
    potongan_per_keterlambatan: int = Field(
        default=25000,
        ge=0,
        description="Nominal potongan per kejadian keterlambatan (AC4). Default: Rp 25.000/kejadian"
    )


# ==============================================================================
# REQUEST: HITUNG GAJI (input dari FE ke BE M14)
# ==============================================================================

class HitungGajiRequest(BaseModel):
    """
    Request body untuk endpoint POST /api/salary-calculation/hitung
    Frontend mengirim daftar karyawan + periode + (opsional) aturan potongan.
    """
    employee_ids: List[int] = Field(
        ...,
        min_length=1,
        description="Daftar ID karyawan yang akan dihitung gajinya"
    )
    periode_bulan: int = Field(..., ge=1, le=12, description="Bulan periode (1-12)")
    periode_tahun: int = Field(..., ge=2000, description="Tahun periode")
    aturan_potongan: Optional[DeductionRules] = Field(
        default=None,
        description="Aturan potongan kustom. Jika kosong, pakai default sistem."
    )


# ==============================================================================
# HASIL PERHITUNGAN PER KARYAWAN (U2-T3 / AC1, AC5)
# ==============================================================================

class RincianGaji(BaseModel):
    """
    Rincian lengkap hasil perhitungan gaji per karyawan (AC5).
    """
    gaji_pokok: int = Field(..., description="Gaji pokok dari komponen gaji (US1)")
    total_tunjangan: int = Field(..., description="Total semua tunjangan (fixed + itemized)")
    potongan_tetap: int = Field(..., description="Potongan tetap dari komponen gaji (US1)")
    potongan_alpa: int = Field(..., description="Nominal potongan akibat alpa (AC3)")
    potongan_keterlambatan: int = Field(..., description="Nominal potongan akibat keterlambatan (AC4)")
    total_potongan: int = Field(..., description="Total semua potongan")
    gaji_bersih: int = Field(..., description="Gaji bersih = gaji_pokok + tunjangan - total_potongan (AC1)")


class HasilPerhitunganKaryawan(BaseModel):
    """
    Hasil perhitungan gaji untuk satu karyawan (AC1, AC5, AC7).
    """
    employee_id: int
    employee_name: str
    nik: str
    department: str
    position: str
    periode_bulan: int
    periode_tahun: int
    rekap_kehadiran: RekapKehadiranM13
    rincian_gaji: RincianGaji
    is_negatif: bool = Field(
        default=False,
        description="True jika gaji bersih negatif - ditandai untuk ditinjau (AC7, tidak dibulatkan)"
    )
    catatan: Optional[str] = Field(
        default=None,
        description="Catatan tambahan, mis. peringatan gaji negatif"
    )


# ==============================================================================
# RESPONSE WRAPPER
# ==============================================================================

class KaryawanDilewati(BaseModel):
    """Data karyawan yang dilewati saat perhitungan (AC6)."""
    employee_id: int
    employee_name: str
    alasan: str


class HitungGajiResponse(BaseModel):
    """Response dari endpoint hitung gaji."""
    periode_bulan: int
    periode_tahun: int
    jumlah_karyawan: int
    hasil: List[HasilPerhitunganKaryawan]
    karyawan_dilewati: List[KaryawanDilewati] = Field(
        default_factory=list,
        description="Daftar karyawan yang dilewati karena komponen gaji belum diatur (AC6)"
    )
    peringatan: List[str] = Field(
        default_factory=list,
        description="Pesan peringatan untuk karyawan yang dilewati (AC6)"
    )
    aturan_potongan_digunakan: DeductionRules


class SalaryCalculationRecord(BaseModel):
    """
    Record tersimpan di database M14 untuk audit trail hasil perhitungan (U2-T5 / AC5).
    """
    id: Optional[str] = None
    employee_id: int
    employee_name: str
    periode_bulan: int
    periode_tahun: int
    gaji_pokok: int
    total_tunjangan: int
    potongan_tetap: int
    potongan_alpa: int
    potongan_keterlambatan: int
    total_potongan: int
    gaji_bersih: int
    is_negatif: bool
    jumlah_alpa: int
    jumlah_keterlambatan: int
    dihitung_oleh: str
    dihitung_pada: str


class ListSalaryCalculationResponse(BaseModel):
    """Response untuk list riwayat perhitungan."""
    data: List[SalaryCalculationRecord]
    total: int


# ==============================================================================
# SCHEMA STATUS PENGUNCIAN PERIODE (U2-T10 / AC8)
# ==============================================================================

class KunciPeriodeRequest(BaseModel):
    """Request untuk mengunci / membuka kunci periode penggajian."""
    periode_bulan: int = Field(..., ge=1, le=12, description="Bulan periode (1-12)")
    periode_tahun: int = Field(..., ge=2000, description="Tahun periode")


class PeriodeStatusResponse(BaseModel):
    """Response status penguncian periode penggajian."""
    periode_bulan: int
    periode_tahun: int
    is_locked: bool
    locked_at: Optional[str] = None
    locked_by: Optional[str] = None
    total_karyawan_terhitung: int = 0
