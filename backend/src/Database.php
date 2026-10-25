<?php

declare(strict_types=1);

namespace App;

use PDO;

final class Database
{
    private static ?PDO $instance = null;

    public static function getConnection(): PDO
    {
        if (self::$instance === null) {
            $dbPath = dirname(__DIR__) . '/database/database.sqlite';
            $isNew = !file_exists($dbPath);

            self::$instance = new PDO("sqlite:{$dbPath}", null, null, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            ]);

            if ($isNew) {
                self::initSchema(self::$instance);
                self::seedData(self::$instance);
            }
        }

        return self::$instance;
    }

    private static function initSchema(PDO $pdo): void
    {
        $pdo->exec(<<<SQL
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
SQL
        );
    }

    private static function seedData(PDO $pdo): void
    {
        $now = date('c');

        $employees = [
            [1, 'Andi Pratama', '2026001', 'Operasional', 'Staf Operasional', $now],
            [2, 'Siti Rahma', '2026002', 'Keuangan', 'Staf Keuangan', $now],
            [3, 'Budi Santoso', '2026003', 'Sumber Daya Manusia', 'Staf HR', $now],
            [4, 'Dewi Lestari', '2026004', 'Operasional', 'Supervisor', $now],
            [5, 'Rizky Firmansyah', '2026005', 'Teknologi Informasi', 'Staf IT', $now],
        ];

        $stmt = $pdo->prepare('
            INSERT INTO employees (id, name, nik, department, position, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ');
        foreach ($employees as $emp) {
            $stmt->execute($emp);
        }

        // Andi Pratama (id: 1)
        $pdo->prepare('
            INSERT INTO salary_components (id, employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
            VALUES (1, 1, 5000000, 750000, 100000, "2026-11-01", ?)
        ')->execute([$now]);

        $pdo->prepare('
            INSERT INTO salary_items (id, salary_component_id, type, name, amount)
            VALUES 
                ("al-1-1", 1, "allowance", "Tunjangan Transport", 500000),
                ("al-1-2", 1, "allowance", "Tunjangan Makan", 250000),
                ("de-1-1", 1, "deduction", "BPJS Ketenagakerjaan", 100000)
        ')->execute();

        // Budi Santoso (id: 3)
        $pdo->prepare('
            INSERT INTO salary_components (id, employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
            VALUES (2, 3, 4800000, 500000, 0, "2026-11-01", ?)
        ')->execute([$now]);

        $pdo->prepare('
            INSERT INTO salary_items (id, salary_component_id, type, name, amount)
            VALUES 
                ("al-3-1", 2, "allowance", "Tunjangan Kehadiran", 500000)
        ')->execute();

        // Sample History
        $histOld1 = json_encode([
            'basicSalary' => 4500000,
            'fixedAllowance' => 500000,
            'deduction' => 100000,
            'allowances' => [['id' => 'h1-1', 'name' => 'Tunjangan Transport', 'amount' => 500000]],
            'deductions' => [['id' => 'h1-2', 'name' => 'BPJS Ketenagakerjaan', 'amount' => 100000]],
        ]);
        $histNew1 = json_encode([
            'basicSalary' => 5000000,
            'fixedAllowance' => 750000,
            'deduction' => 100000,
            'allowances' => [
                ['id' => 'h1-3', 'name' => 'Tunjangan Transport', 'amount' => 500000],
                ['id' => 'h1-4', 'name' => 'Tunjangan Makan', 'amount' => 250000],
            ],
            'deductions' => [['id' => 'h1-5', 'name' => 'BPJS Ketenagakerjaan', 'amount' => 100000]],
        ]);
        $pdo->prepare('
            INSERT INTO salary_history (id, employee_id, old_value, new_value, changed_by, changed_at)
            VALUES ("hist-1", 1, ?, ?, "Rani K. (Admin HR)", "2026-10-20T09:15:00+07:00")
        ')->execute([$histOld1, $histNew1]);

        // Seed Users with Roles
        $userStmt = $pdo->prepare('
            INSERT INTO users (id, name, email, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        ');
        $userStmt->execute([1, 'Rani K.', 'rani.hr@araya.com', 'Admin HR', $now]);
        $userStmt->execute([2, 'Andi Pratama', 'andi@araya.com', 'Employee', $now]);
    }
}
