import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, Any
from dotenv import load_dotenv

# Muat variabel environment dari .env jika ada
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))

DB_DIR = os.path.join(BASE_DIR, "database")
SQLITE_PATH = os.path.join(DB_DIR, "database.sqlite")

# Cek apakah konfigurasi Neon Console (PostgreSQL) disediakan
def get_database_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")
    if url and url.strip():
        raw = url.strip()
        # Normalisasi prefix postgres:// menjadi postgresql://
        if raw.startswith("postgres://"):
            raw = "postgresql://" + raw[len("postgres://"):]
        return raw
    return None

def is_postgres() -> bool:
    url = get_database_url()
    return url is not None and url.startswith("postgresql://")

# ==============================================================================
# POSTGRESQL (NEON CONSOLE) ADAPTER
# ==============================================================================
class PostgresCursorWrapper:
    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, query: str, params: Any = None):
        # Konversi parameter placeholder SQLite (?) menjadi placeholder PostgreSQL (%s)
        adapted_query = query.replace("?", "%s")
        if params is not None:
            self._cur.execute(adapted_query, params)
        else:
            self._cur.execute(adapted_query)
        return self

    def executemany(self, query: str, params_seq):
        adapted_query = query.replace("?", "%s")
        self._cur.executemany(adapted_query, params_seq)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        self._cur.close()

    def __iter__(self):
        return iter(self._cur)


class PostgresConnectionWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        import psycopg2.extras
        # Gunakan DictCursor agar bisa diakses baik via dict (row["id"]) maupun index (row[0])
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def executescript(self, sql_script: str):
        with self._conn.cursor() as cur:
            cur.execute(sql_script)

    def __enter__(self):
        self._conn.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)


# ==============================================================================
# CONNECTION FACTORY
# ==============================================================================
def get_db_connection():
    db_url = get_database_url()
    if is_postgres():
        import psycopg2
        # Neon Console memerlukan SSL
        conn = psycopg2.connect(db_url, sslmode="require")
        return PostgresConnectionWrapper(conn)

    # Fallback default: SQLite lokal
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ==============================================================================
# DATABASE INITIALIZATION & SEEDER
# ==============================================================================
def init_db():
    if is_postgres():
        init_postgres_db()
    else:
        init_sqlite_db()


def init_sqlite_db():
    os.makedirs(DB_DIR, exist_ok=True)
    print(f"[Database] Mode: SQLite lokal ({SQLITE_PATH})")
    
    conn = get_db_connection()
    with conn:
        conn.executescript("""
            -- CATATAN: Tabel 'employees' TIDAK ada di database M14.
            -- Data karyawan diambil dari API M12 (M12_API_BASE_URL).
            -- employee_id di tabel berikut adalah referensi integer ke ID karyawan M12.

            CREATE TABLE IF NOT EXISTS salary_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL UNIQUE,
                basic_salary INTEGER NOT NULL,
                fixed_allowance INTEGER NOT NULL DEFAULT 0,
                deduction INTEGER NOT NULL DEFAULT 0,
                effective_from TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS salary_items (
                id TEXT PRIMARY KEY,
                salary_component_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                amount INTEGER NOT NULL,
                FOREIGN KEY (salary_component_id) REFERENCES salary_components(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS salary_history (
                id TEXT PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                old_value TEXT,
                new_value TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                changed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'Employee',
                created_at TEXT NOT NULL
            );

            -- US2: Tabel hasil perhitungan gaji berdasarkan kehadiran (U2-T5)
            -- Data karyawan diambil dari API M12, rekap kehadiran dari API M13.
            -- Tabel ini sepenuhnya milik database M14.
            CREATE TABLE IF NOT EXISTS salary_calculations (
                id TEXT PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                employee_name TEXT NOT NULL,
                periode_bulan INTEGER NOT NULL,
                periode_tahun INTEGER NOT NULL,
                gaji_pokok INTEGER NOT NULL,
                total_tunjangan INTEGER NOT NULL DEFAULT 0,
                potongan_tetap INTEGER NOT NULL DEFAULT 0,
                potongan_alpa INTEGER NOT NULL DEFAULT 0,
                potongan_keterlambatan INTEGER NOT NULL DEFAULT 0,
                total_potongan INTEGER NOT NULL DEFAULT 0,
                gaji_bersih INTEGER NOT NULL,
                is_negatif INTEGER NOT NULL DEFAULT 0,
                jumlah_alpa INTEGER NOT NULL DEFAULT 0,
                jumlah_keterlambatan INTEGER NOT NULL DEFAULT 0,
                dihitung_oleh TEXT NOT NULL,
                dihitung_pada TEXT NOT NULL
            );

            -- US2: Tabel status penguncian periode penggajian (U2-T10 / AC8)
            CREATE TABLE IF NOT EXISTS payroll_periods (
                id TEXT PRIMARY KEY,
                periode_bulan INTEGER NOT NULL,
                periode_tahun INTEGER NOT NULL,
                is_locked INTEGER NOT NULL DEFAULT 0,
                locked_at TEXT,
                locked_by TEXT,
                created_at TEXT NOT NULL
            );
        """)

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM salary_components")
        count = cursor.fetchone()[0]
        if count == 0:
            seed_data(conn, db_type="sqlite")

    conn.close()


def init_postgres_db():
    print("[Database] Mode: Neon Console (PostgreSQL)")
    conn = get_db_connection()
    try:
        with conn:
            conn.executescript("""
                -- CATATAN: Tabel 'employees' TIDAK ada di database M14.
                -- Data karyawan diambil dari API M12 (M12_API_BASE_URL).
                -- employee_id di tabel berikut adalah referensi integer ke ID karyawan M12.

                CREATE TABLE IF NOT EXISTS salary_components (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL UNIQUE,
                    basic_salary BIGINT NOT NULL,
                    fixed_allowance BIGINT NOT NULL DEFAULT 0,
                    deduction BIGINT NOT NULL DEFAULT 0,
                    effective_from VARCHAR(50) NOT NULL,
                    updated_at VARCHAR(100) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS salary_items (
                    id VARCHAR(100) PRIMARY KEY,
                    salary_component_id INTEGER NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    amount BIGINT NOT NULL,
                    FOREIGN KEY (salary_component_id) REFERENCES salary_components(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS salary_history (
                    id VARCHAR(100) PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    old_value TEXT,
                    new_value TEXT NOT NULL,
                    changed_by VARCHAR(255) NOT NULL,
                    changed_at VARCHAR(100) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    role VARCHAR(50) NOT NULL DEFAULT 'Employee',
                    created_at VARCHAR(100) NOT NULL
                );

                -- US2: Tabel hasil perhitungan gaji berdasarkan kehadiran (U2-T5)
                -- Data karyawan diambil dari API M12, rekap kehadiran dari API M13.
                -- Tabel ini sepenuhnya milik database M14.
                CREATE TABLE IF NOT EXISTS salary_calculations (
                    id VARCHAR(100) PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    employee_name VARCHAR(255) NOT NULL,
                    periode_bulan INTEGER NOT NULL,
                    periode_tahun INTEGER NOT NULL,
                    gaji_pokok BIGINT NOT NULL,
                    total_tunjangan BIGINT NOT NULL DEFAULT 0,
                    potongan_tetap BIGINT NOT NULL DEFAULT 0,
                    potongan_alpa BIGINT NOT NULL DEFAULT 0,
                    potongan_keterlambatan BIGINT NOT NULL DEFAULT 0,
                    total_potongan BIGINT NOT NULL DEFAULT 0,
                    gaji_bersih BIGINT NOT NULL,
                    is_negatif BOOLEAN NOT NULL DEFAULT FALSE,
                    jumlah_alpa INTEGER NOT NULL DEFAULT 0,
                    jumlah_keterlambatan INTEGER NOT NULL DEFAULT 0,
                    dihitung_oleh VARCHAR(255) NOT NULL,
                    dihitung_pada VARCHAR(100) NOT NULL
                );

                -- US2: Tabel status penguncian periode penggajian (U2-T10 / AC8)
                CREATE TABLE IF NOT EXISTS payroll_periods (
                    id VARCHAR(50) PRIMARY KEY,
                    periode_bulan INTEGER NOT NULL,
                    periode_tahun INTEGER NOT NULL,
                    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
                    locked_at VARCHAR(100),
                    locked_by VARCHAR(255),
                    created_at VARCHAR(100) NOT NULL
                );
            """)

            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM salary_components")
            count = cursor.fetchone()[0]
            if count == 0:
                seed_data(conn, db_type="postgres")
    finally:
        conn.close()


def seed_data(conn, db_type: str = "sqlite"):
    now = datetime.now().isoformat()

    # ----------------------------------------------------------------
    # CATATAN: Tidak ada seed data karyawan di sini.
    # Data karyawan diambil dari API M12 (M12_API_BASE_URL).
    # employee_id di bawah (1, 3) harus sesuai dengan ID karyawan di M12.
    # ----------------------------------------------------------------
    cursor = conn.cursor()

    # Gunakan placeholder yang sesuai: %s untuk PostgreSQL, ? untuk SQLite
    ph = "%s" if db_type == "postgres" else "?"

    # Komponen Gaji karyawan ID 1 (sesuaikan dengan ID karyawan di M12)
    cursor.execute(f"""
        INSERT INTO salary_components (id, employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
        VALUES (1, 1, 5000000, 750000, 100000, '2026-11-01', {ph})
    """, (now,))

    cursor.executemany(f"""
        INSERT INTO salary_items (id, salary_component_id, type, name, amount)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """, [
        ("al-1-1", 1, "allowance", "Tunjangan Transport", 500000),
        ("al-1-2", 1, "allowance", "Tunjangan Makan", 250000),
        ("de-1-1", 1, "deduction", "BPJS Ketenagakerjaan", 100000),
    ])

    # Komponen Gaji karyawan ID 3 (sesuaikan dengan ID karyawan di M12)
    cursor.execute(f"""
        INSERT INTO salary_components (id, employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
        VALUES (2, 3, 4800000, 500000, 0, '2026-11-01', {ph})
    """, (now,))

    cursor.executemany(f"""
        INSERT INTO salary_items (id, salary_component_id, type, name, amount)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """, [
        ("al-3-1", 2, "allowance", "Tunjangan Kehadiran", 500000),
    ])

    # Sample History
    hist_old1 = json.dumps({
        "basicSalary": 4500000,
        "fixedAllowance": 500000,
        "deduction": 100000,
        "allowances": [{"id": "h1-1", "name": "Tunjangan Transport", "amount": 500000}],
        "deductions": [{"id": "h1-2", "name": "BPJS Ketenagakerjaan", "amount": 100000}],
    })
    hist_new1 = json.dumps({
        "basicSalary": 5000000,
        "fixedAllowance": 750000,
        "deduction": 100000,
        "allowances": [
            {"id": "h1-3", "name": "Tunjangan Transport", "amount": 500000},
            {"id": "h1-4", "name": "Tunjangan Makan", "amount": 250000},
        ],
        "deductions": [{"id": "h1-5", "name": "BPJS Ketenagakerjaan", "amount": 100000}],
    })

    cursor.execute(f"""
        INSERT INTO salary_history (id, employee_id, old_value, new_value, changed_by, changed_at)
        VALUES ('hist-1', 1, {ph}, {ph}, 'Rani K. (Admin HR)', '2026-10-20T09:15:00+07:00')
    """, (hist_old1, hist_new1))

    # Seed Users (untuk autentikasi role M14)
    users = [
        (1, "Rani K.", "rani.hr@araya.com", "Admin HR", now),
        (2, "Andi Pratama", "andi@araya.com", "Employee", now),
    ]
    cursor.executemany(
        f"INSERT INTO users (id, name, email, role, created_at) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
        users
    )

    # Khusus PostgreSQL: sinkronisasi sequence auto-increment
    if db_type == "postgres":
        cursor.execute("SELECT setval('salary_components_id_seq', (SELECT MAX(id) FROM salary_components));")
        cursor.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));")

    conn.commit()
