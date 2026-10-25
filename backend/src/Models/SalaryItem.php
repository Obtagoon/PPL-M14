<?php

declare(strict_types=1);

namespace App\Models;

final readonly class SalaryItem
{
    public function __construct(
        public string $id,
        public string $name,
        public int $amount,
        public string $type = 'allowance',
    ) {}

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'amount' => $this->amount,
        ];
    }
}
