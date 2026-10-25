-- ========================================================
-- Schema Database PPL-M14 untuk PostgreSQL (Neon Console)
-- ========================================================

-- 1. Tabel Karyawan
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    nik VARCHAR(50) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    created_at VARCHAR(100) NOT NULL
);

-- 2. Tabel Komponen Gaji Utama (AC1)
CREATE TABLE IF NOT EXISTS salary_components (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL UNIQUE,
    basic_salary BIGINT NOT NULL,
    fixed_allowance BIGINT NOT NULL DEFAULT 0,
    deduction BIGINT NOT NULL DEFAULT 0,
    effective_from VARCHAR(50) NOT NULL,
    updated_at VARCHAR(100) NOT NULL,
    CONSTRAINT fk_salary_components_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- 3. Tabel Item Rincian Tunjangan & Potongan (AC4)
CREATE TABLE IF NOT EXISTS salary_items (
    id VARCHAR(100) PRIMARY KEY,
    salary_component_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'allowance' atau 'deduction'
    name VARCHAR(255) NOT NULL,
    amount BIGINT NOT NULL,
    CONSTRAINT fk_salary_items_component FOREIGN KEY (salary_component_id) REFERENCES salary_components(id) ON DELETE CASCADE
);

-- 4. Tabel Riwayat Audit Perubahan Komponen Gaji
CREATE TABLE IF NOT EXISTS salary_history (
    id VARCHAR(100) PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    changed_by VARCHAR(255) NOT NULL,
    changed_at VARCHAR(100) NOT NULL,
    CONSTRAINT fk_salary_history_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- 5. Tabel User / RBAC
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'Employee',
    created_at VARCHAR(100) NOT NULL
);

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_salary_components_employee_id ON salary_components(employee_id);
CREATE INDEX IF NOT EXISTS idx_salary_items_comp_id ON salary_items(salary_component_id);
CREATE INDEX IF NOT EXISTS idx_salary_history_employee_id ON salary_history(employee_id);

-- Data Seeder Awal (Opsional jika dijalankan manual di Neon SQL Console)
INSERT INTO employees (id, name, nik, department, position, created_at)
VALUES 
    (1, 'Andi Pratama', '2026001', 'Operasional', 'Staf Operasional', NOW()::text),
    (2, 'Siti Rahma', '2026002', 'Keuangan', 'Staf Keuangan', NOW()::text),
    (3, 'Budi Santoso', '2026003', 'Sumber Daya Manusia', 'Staf HR', NOW()::text),
    (4, 'Dewi Lestari', '2026004', 'Operasional', 'Supervisor', NOW()::text),
    (5, 'Rizky Firmansyah', '2026005', 'Teknologi Informasi', 'Staf IT', NOW()::text)
ON CONFLICT (id) DO NOTHING;

INSERT INTO salary_components (id, employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
VALUES 
    (1, 1, 5000000, 750000, 100000, '2026-11-01', NOW()::text),
    (2, 3, 4800000, 500000, 0, '2026-11-01', NOW()::text)
ON CONFLICT (id) DO NOTHING;

INSERT INTO salary_items (id, salary_component_id, type, name, amount)
VALUES 
    ('al-1-1', 1, 'allowance', 'Tunjangan Transport', 500000),
    ('al-1-2', 1, 'allowance', 'Tunjangan Makan', 250000),
    ('de-1-1', 1, 'deduction', 'BPJS Ketenagakerjaan', 100000),
    ('al-3-1', 2, 'allowance', 'Tunjangan Kehadiran', 500000)
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, name, email, role, created_at)
VALUES 
    (1, 'Rani K.', 'rani.hr@araya.com', 'Admin HR', NOW()::text),
    (2, 'Andi Pratama', 'andi@araya.com', 'Employee', NOW()::text)
ON CONFLICT (id) DO NOTHING;

-- Sinkronisasi sequence auto-increment
SELECT setval('employees_id_seq', COALESCE((SELECT MAX(id) FROM employees), 1));
SELECT setval('salary_components_id_seq', COALESCE((SELECT MAX(id) FROM salary_components), 1));
SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1));
