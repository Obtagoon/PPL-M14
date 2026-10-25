<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Database;
use InvalidArgumentException;
use PDO;

final class SalaryComponentController
{
    public function show(int $employeeId): ?array
    {
        $pdo = Database::getConnection();

        $stmt = $pdo->prepare('
            SELECT id, basic_salary, fixed_allowance, deduction, effective_from
            FROM salary_components
            WHERE employee_id = ?
        ');
        $stmt->execute([$employeeId]);
        $comp = $stmt->fetch();

        if (!$comp) {
            return null;
        }

        $itemStmt = $pdo->prepare('
            SELECT id, name, amount, type
            FROM salary_items
            WHERE salary_component_id = ?
            ORDER BY rowid ASC
        ');
        $itemStmt->execute([$comp['id']]);
        $items = $itemStmt->fetchAll();

        $allowances = [];
        $deductions = [];

        foreach ($items as $item) {
            $entry = [
                'id' => (string) $item['id'],
                'name' => (string) $item['name'],
                'amount' => (int) $item['amount'],
            ];
            if ($item['type'] === 'allowance') {
                $allowances[] = $entry;
            } else {
                $deductions[] = $entry;
            }
        }

        return [
            'basicSalary' => (int) $comp['basic_salary'],
            'fixedAllowance' => (int) $comp['fixed_allowance'],
            'deduction' => (int) $comp['deduction'],
            'effectiveFrom' => (string) $comp['effective_from'],
            'allowances' => $allowances,
            'deductions' => $deductions,
        ];
    }

    public function save(int $employeeId, array $payload, bool $isUpdate, string $changedBy = 'Rani K. (Admin HR)'): array
    {
        $pdo = Database::getConnection();

        // 1. Check employee exists
        $empStmt = $pdo->prepare('SELECT id, name FROM employees WHERE id = ?');
        $empStmt->execute([$employeeId]);
        $employee = $empStmt->fetch();
        if (!$employee) {
            throw new InvalidArgumentException('Karyawan tidak ditemukan.');
        }

        // 2. Validation (AC1 & AC4)
        $basicSalary = isset($payload['basicSalary']) ? (int) $payload['basicSalary'] : 0;
        if ($basicSalary <= 0) {
            throw new InvalidArgumentException('Gaji pokok wajib diisi dan harus lebih besar dari Rp 0.');
        }

        $effectiveFrom = !empty($payload['effectiveFrom']) ? (string) $payload['effectiveFrom'] : date('Y-m-01', strtotime('+1 month'));

        $allowances = [];
        $totalAllowance = 0;
        if (!empty($payload['allowances']) && is_array($payload['allowances'])) {
            foreach ($payload['allowances'] as $idx => $item) {
                $name = trim((string) ($item['name'] ?? ''));
                $amt = (int) ($item['amount'] ?? 0);
                if ($name === '') {
                    throw new InvalidArgumentException("Nama tunjangan ke-" . ($idx + 1) . " tidak boleh kosong.");
                }
                if ($amt < 0) {
                    throw new InvalidArgumentException("Nominal tunjangan '{$name}' tidak boleh bernilai negatif.");
                }
                $itemId = !empty($item['id']) ? (string) $item['id'] : 'al-' . bin2hex(random_bytes(4));
                $allowances[] = ['id' => $itemId, 'name' => $name, 'amount' => $amt, 'type' => 'allowance'];
                $totalAllowance += $amt;
            }
        } else {
            $totalAllowance = isset($payload['fixedAllowance']) ? max(0, (int) $payload['fixedAllowance']) : 0;
        }

        $deductions = [];
        $totalDeduction = 0;
        if (!empty($payload['deductions']) && is_array($payload['deductions'])) {
            foreach ($payload['deductions'] as $idx => $item) {
                $name = trim((string) ($item['name'] ?? ''));
                $amt = (int) ($item['amount'] ?? 0);
                if ($name === '') {
                    throw new InvalidArgumentException("Nama potongan ke-" . ($idx + 1) . " tidak boleh kosong.");
                }
                if ($amt < 0) {
                    throw new InvalidArgumentException("Nominal potongan '{$name}' tidak boleh bernilai negatif.");
                }
                $itemId = !empty($item['id']) ? (string) $item['id'] : 'de-' . bin2hex(random_bytes(4));
                $deductions[] = ['id' => $itemId, 'name' => $name, 'amount' => $amt, 'type' => 'deduction'];
                $totalDeduction += $amt;
            }
        } else {
            $totalDeduction = isset($payload['deduction']) ? max(0, (int) $payload['deduction']) : 0;
        }

        // Get old value for history logging
        $oldSnapshot = $this->show($employeeId);

        $pdo->beginTransaction();
        try {
            $now = date('c');

            // Find existing salary component
            $compStmt = $pdo->prepare('SELECT id FROM salary_components WHERE employee_id = ?');
            $compStmt->execute([$employeeId]);
            $existing = $compStmt->fetch();

            if ($existing) {
                $componentId = (int) $existing['id'];
                $updateStmt = $pdo->prepare('
                    UPDATE salary_components
                    SET basic_salary = ?, fixed_allowance = ?, deduction = ?, effective_from = ?, updated_at = ?
                    WHERE id = ?
                ');
                $updateStmt->execute([$basicSalary, $totalAllowance, $totalDeduction, $effectiveFrom, $now, $componentId]);

                // Delete old items and insert updated ones
                $pdo->prepare('DELETE FROM salary_items WHERE salary_component_id = ?')->execute([$componentId]);
            } else {
                $insertStmt = $pdo->prepare('
                    INSERT INTO salary_components (employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ');
                $insertStmt->execute([$employeeId, $basicSalary, $totalAllowance, $totalDeduction, $effectiveFrom, $now]);
                $componentId = (int) $pdo->lastInsertId();
            }

            // Insert itemized allowances & deductions (AC4)
            $itemInsertStmt = $pdo->prepare('
                INSERT INTO salary_items (id, salary_component_id, type, name, amount)
                VALUES (?, ?, ?, ?, ?)
            ');
            foreach ($allowances as $al) {
                $itemInsertStmt->execute([$al['id'], $componentId, 'allowance', $al['name'], $al['amount']]);
            }
            foreach ($deductions as $de) {
                $itemInsertStmt->execute([$de['id'], $componentId, 'deduction', $de['name'], $de['amount']]);
            }

            // Save history record
            $newSnapshot = [
                'basicSalary' => $basicSalary,
                'fixedAllowance' => $totalAllowance,
                'deduction' => $totalDeduction,
                'effectiveFrom' => $effectiveFrom,
                'allowances' => array_map(fn($a) => ['id' => $a['id'], 'name' => $a['name'], 'amount' => $a['amount']], $allowances),
                'deductions' => array_map(fn($d) => ['id' => $d['id'], 'name' => $d['name'], 'amount' => $d['amount']], $deductions),
            ];

            $histStmt = $pdo->prepare('
                INSERT INTO salary_history (id, employee_id, old_value, new_value, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ');
                $histStmt->execute([
                    'hist-' . time() . '-' . bin2hex(random_bytes(3)),
                    $employeeId,
                    $oldSnapshot ? json_encode($oldSnapshot) : null,
                    json_encode($newSnapshot),
                    $changedBy,
                    $now,
                ]);

            $pdo->commit();
            return $newSnapshot;
        } catch (\Throwable $e) {
            $pdo->rollBack();
            throw $e;
        }
    }

    public function history(int $employeeId): array
    {
        $pdo = Database::getConnection();

        $stmt = $pdo->prepare('
            SELECT id, employee_id, old_value, new_value, changed_by, changed_at
            FROM salary_history
            WHERE employee_id = ?
            ORDER BY rowid DESC
        ');
        $stmt->execute([$employeeId]);
        $rows = $stmt->fetchAll();

        $result = [];
        foreach ($rows as $row) {
            $result[] = [
                'id' => (string) $row['id'],
                'employeeId' => (int) $row['employee_id'],
                'oldValue' => !empty($row['old_value']) ? json_decode((string) $row['old_value'], true) : null,
                'newValue' => json_decode((string) $row['new_value'], true),
                'changedBy' => (string) $row['changed_by'],
                'changedAt' => (string) $row['changed_at'],
            ];
        }

        return $result;
    }
}
