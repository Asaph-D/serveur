<?php
declare(strict_types=1);

if (!function_exists('str_contains')) {
	function str_contains(string $haystack, string $needle): bool {
		return $needle === '' || strpos($haystack, $needle) !== false;
	}
}

if (!function_exists('str_starts_with')) {
	function str_starts_with(string $haystack, string $needle): bool {
		return $needle === '' || strncmp($haystack, $needle, strlen($needle)) === 0;
	}
}

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/response.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/mail.php';
require_once __DIR__ . '/crypto.php';
require_once __DIR__ . '/extensions.php';
require_once __DIR__ . '/voicemail.php';
require_once __DIR__ . '/vm-notify.php';
require_once __DIR__ . '/chat-messages.php';
require_once __DIR__ . '/tokens.php';
require_once __DIR__ . '/requests.php';
require_once __DIR__ . '/ratelimit.php';
