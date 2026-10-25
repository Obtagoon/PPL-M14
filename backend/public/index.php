<?php

declare(strict_types=1);

// PSR-4 Autoloader fallback
spl_autoload_register(static function (string $class): void {
    $prefix = 'App\\';
    $baseDir = dirname(__DIR__) . '/src/';

    $len = strlen($prefix);
    if (strncmp($prefix, $class, $len) !== 0) {
        return;
    }

    $relativeClass = substr($class, $len);
    $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';

    if (file_exists($file)) {
        require $file;
    }
});

// Set CORS Headers
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, Accept, X-Requested-With, X-User-Role, X-User-Name, *');
header('Access-Control-Max-Age: 86400');
header('Content-Type: application/json; charset=utf-8');

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

function jsonResponse(mixed $data, int $status = 200): void
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    exit;
}

function getJsonBody(): array
{
    $input = file_get_contents('php://input');
    if (empty($input)) {
        return [];
    }
    $decoded = json_decode($input, true);
    return is_array($decoded) ? $decoded : [];
}

try {
    // Health check
    if ($uri === '/' || $uri === '/api' || $uri === '/api/health') {
        jsonResponse([
            'status' => 'ok',
            'message' => 'PPL-M14 Backend API running with PHP ' . PHP_VERSION,
            'version' => '1.0.0',
            'features' => ['AC1: Dasar Perhitungan Gaji', 'AC4: Itemized Tunjangan & Potongan'],
        ]);
    }

    // 1. GET /api/employees
    if ($uri === '/api/employees' && $method === 'GET') {
        $controller = new \App\Controllers\EmployeeController();
        jsonResponse($controller->index());
    }

    // 2. /api/employees/{id}/salary-components
    if (preg_match('#^/api/employees/(\d+)/salary-components$#', $uri, $matches)) {
        $employeeId = (int) $matches[1];
        $controller = new \App\Controllers\SalaryComponentController();

        if ($method === 'GET') {
            $data = $controller->show($employeeId);
            if ($data === null) {
                jsonResponse(['message' => 'Data komponen gaji tidak ditemukan.'], 404);
            }
            jsonResponse(['data' => $data]);
        }

        if ($method === 'POST' || $method === 'PUT') {
            // Otorisasi role: Hanya Admin HR yang berwenang
            $adminUser = \App\Middleware\AuthMiddleware::authorizeAdminHR();

            $body = getJsonBody();
            $saved = $controller->save($employeeId, $body, $method === 'PUT', $adminUser['name']);
            jsonResponse(['data' => $saved]);
        }
    }

    // 3. /api/employees/{id}/salary-history
    if (preg_match('#^/api/employees/(\d+)/salary-history$#', $uri, $matches) && $method === 'GET') {
        $employeeId = (int) $matches[1];
        $controller = new \App\Controllers\SalaryComponentController();
        jsonResponse($controller->history($employeeId));
    }

    // 404 Not Found
    jsonResponse(['message' => "Route '{$method} {$uri}' tidak ditemukan."], 404);
} catch (\InvalidArgumentException $e) {
    jsonResponse(['message' => $e->getMessage()], 422);
} catch (\Throwable $e) {
    jsonResponse([
        'message' => 'Internal server error: ' . $e->getMessage(),
    ], 500);
}

