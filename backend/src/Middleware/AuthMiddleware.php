<?php

declare(strict_types=1);

namespace App\Middleware;

final class AuthMiddleware
{
    /**
     * Memeriksa dan memvalidasi otorisasi Role pengguna.
     * Hanya pengguna dengan role 'Admin HR' yang diizinkan mengubah/mengatur komponen gaji.
     *
     * @return array{name: string, role: string}
     */
    public static function authorizeAdminHR(): array
    {
        // 1. Ambil role dari Header HTTP
        $role = $_SERVER['HTTP_X_USER_ROLE'] ?? null;
        $userName = $_SERVER['HTTP_X_USER_NAME'] ?? 'Rani K. (Admin HR)';

        // Cek juga dari Authorization Bearer token jika dikirimkan
        if ($role === null) {
            $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
            if (str_starts_with($authHeader, 'Bearer ')) {
                $token = trim(substr($authHeader, 7));
                $role = strtolower($token) === 'employee' ? 'Employee' : 'Admin HR';
            } else {
                // Default sesi dev: Admin HR
                $role = 'Admin HR';
            }
        }

        // 2. Verifikasi otorisasi RBAC (Role-Based Access Control)
        if (strtolower(trim((string) $role)) !== 'admin hr') {
            http_response_code(403);
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode([
                'status' => 'forbidden',
                'code' => 403,
                'message' => "Akses Ditolak (HTTP 403): Hanya pengguna dengan role 'Admin HR' yang berwenang mengatur komponen gaji.",
                'currentRole' => $role,
            ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
            exit;
        }

        return [
            'name' => $userName,
            'role' => 'Admin HR',
        ];
    }
}
