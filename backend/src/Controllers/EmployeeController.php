<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Database;
use PDO;

final class EmployeeController
{
    public function index(): array
    {
        $pdo = Database::getConnection();

        $stmt = $pdo->query('
            SELECT id, name, nik, department, position, created_at
            FROM employees
            ORDER BY id ASC
        ');
        $employees = $stmt->fetchAll();

        $compStmt = $pdo->prepare('
            SELECT id, basic_salary, fixed_allowance, deduction, effective_from
            FROM salary_components
            WHERE employee_id = ?
        ');

        $itemStmt = $pdo->prepare('
            SELECT id, name, amount, type
            FROM salary_items
            WHERE salary_component_id = ?
            ORDER BY rowid ASC
        ');

        $result = [];
        foreach ($employees as $emp) {
            $compStmt->execute([$emp['id']]);
            $comp = $compStmt->fetch();

            $salaryComponent = null;
            if ($comp) {
                $itemStmt->execute([$comp['id']]);
                $items = $itemStmt->fetchAll();

                $allowances = [];
                $deductions = [];

                foreach ($items as $item) {
                    $itemData = [
                        'id' => (string) $item['id'],
                        'name' => (string) $item['name'],
                        'amount' => (int) $item['amount'],
                    ];
                    if ($item['type'] === 'allowance') {
                        $allowances[] = $itemData;
                    } else {
                        $deductions[] = $itemData;
                    }
                }

                $salaryComponent = [
                    'basicSalary' => (int) $comp['basic_salary'],
                    'fixedAllowance' => (int) $comp['fixed_allowance'],
                    'deduction' => (int) $comp['deduction'],
                    'effectiveFrom' => (string) $comp['effective_from'],
                    'allowances' => $allowances,
                    'deductions' => $deductions,
                ];
            }

            $result[] = [
                'id' => (int) $emp['id'],
                'name' => (string) $emp['name'],
                'nik' => (string) $emp['nik'],
                'department' => (string) $emp['department'],
                'position' => (string) $emp['position'],
                'salaryComponent' => $salaryComponent,
            ];
        }

        return $result;
    }
}
