<?php
declare(strict_types=1);

if (!function_exists('str_contains')) {
	function str_contains(string $haystack, string $needle): bool {
		return $needle === '' || strpos($haystack, $needle) !== false;
	}
}

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/response.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/mail.php';
require_once __DIR__ . '/crypto.php';
require_once __DIR__ . '/extensions.php';
require_once __DIR__ . '/tokens.php';
require_once __DIR__ . '/requests.php';
require_once __DIR__ . '/ratelimit.php';
