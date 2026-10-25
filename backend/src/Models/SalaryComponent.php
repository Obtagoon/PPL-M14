<?php

declare(strict_types=1);

namespace App\Models;

final readonly class SalaryComponent
{
    /**
     * @param SalaryItem[] $allowances
     * @param SalaryItem[] $deductions
     */
    public function __construct(
        public int $basicSalary,
        public int $fixedAllowance,
        public int $deduction,
        public string $effectiveFrom,
        public array $allowances = [],
        public array $deductions = [],
    ) {}

    public function getNetSalary(): int
    {
        return max(0, $this->basicSalary + $this->fixedAllowance - $this->deduction);
    }

    public function toArray(): array
    {
        return [
            'basicSalary' => $this->basicSalary,
            'fixedAllowance' => $this->fixedAllowance,
            'deduction' => $this->deduction,
            'effectiveFrom' => $this->effectiveFrom,
            'netSalary' => $this->getNetSalary(),
            'allowances' => array_map(static fn (SalaryItem $item): array => $item->toArray(), $this->allowances),
            'deductions' => array_map(static fn (SalaryItem $item): array => $item->toArray(), $this->deductions),
        ];
    }
}
