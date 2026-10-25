import os
import sqlite3
import json
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "database.sqlite")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    is_new = not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0
    
    conn = get_db_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                nik TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                position TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS salary_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL UNIQUE,
                basic_salary INTEGER NOT NULL,
                fixed_allowance INTEGER NOT NULL DEFAULT 0,
                deduction INTEGER NOT NULL DEFAULT 0,
                effective_from TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS salary_items (
                id TEXT PRIMARY KEY,
                salary_component_id INTEGER NOT NULL,
                type TEXT NOT NULL, -- "allowance" or "deduction"
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
                changed_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'Employee',
                created_at TEXT NOT NULL
            );
        """)

        # Cek apakah seeder perlu dijalankan
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM employees")
        count = cursor.fetchone()[0]
        if count == 0:
            seed_data(conn)

    conn.close()

def seed_data(conn: sqlite3.Connection):
    now = datetime.now().isoformat()

    employees = [
        (1, "Andi Pratama", "2026001", "Operasional", "Staf Operasional", now),
        (2, "Siti Rahma", "2026002", "Keuangan", "Staf Keuangan", now),
        (3, "Budi Santoso", "2026003", "Sumber Daya Manusia", "Staf HR", now),
        (4, "Dewi Lestari", "2026004", "Operasional", "Supervisor", now),
        (5, "Rizky Firmansyah", "2026005", "Teknologi Informasi", "Staf IT", now),
    ]

    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO employees (id, name, nik, department, position, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        employees
    )

    # Andi Pratama (id: 1)
    cursor.execute("""
        INSERT INTO salary_components (id, employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
        VALUES (1, 1, 5000000, 750000, 100000, "2026-11-01", ?)
    """, (now,))

    cursor.executemany("""
        INSERT INTO salary_items (id, salary_component_id, type, name, amount)
        VALUES (?, ?, ?, ?, ?)
    """, [
        ("al-1-1", 1, "allowance", "Tunjangan Transport", 500000),
        ("al-1-2", 1, "allowance", "Tunjangan Makan", 250000),
        ("de-1-1", 1, "deduction", "BPJS Ketenagakerjaan", 100000),
    ])

    # Budi Santoso (id: 3)
    cursor.execute("""
        INSERT INTO salary_components (id, employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
        VALUES (2, 3, 4800000, 500000, 0, "2026-11-01", ?)
    """, (now,))

    cursor.executemany("""
        INSERT INTO salary_items (id, salary_component_id, type, name, amount)
        VALUES (?, ?, ?, ?, ?)
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

    cursor.execute("""
        INSERT INTO salary_history (id, employee_id, old_value, new_value, changed_by, changed_at)
        VALUES ("hist-1", 1, ?, ?, "Rani K. (Admin HR)", "2026-10-20T09:15:00+07:00")
    """, (hist_old1, hist_new1))

    # Seed Users
    users = [
        (1, "Rani K.", "rani.hr@araya.com", "Admin HR", now),
        (2, "Andi Pratama", "andi@araya.com", "Employee", now),
    ]
    cursor.executemany(
        "INSERT INTO users (id, name, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
        users
    )
    conn.commit()
