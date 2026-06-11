<?php
declare(strict_types=1);

function provision_rate_limit(string $scope, string $identifier, int $maxHits, int $windowSeconds = 3600): void {
	$db = provision_pdo();
	$now = new DateTimeImmutable('now');
	$windowStart = $now->modify('-' . $windowSeconds . ' seconds');

	$db->prepare('DELETE FROM provision_rate_limits WHERE window_start < ?')
		->execute([$windowStart->format('Y-m-d H:i:s')]);

	$sth = $db->prepare(
		'SELECT id, hits, window_start FROM provision_rate_limits
		 WHERE scope = ? AND identifier = ? LIMIT 1'
	);
	$sth->execute([$scope, $identifier]);
	$row = $sth->fetch();

	if (!$row) {
		$ins = $db->prepare(
			'INSERT INTO provision_rate_limits (scope, identifier, hits, window_start)
			 VALUES (?, ?, 1, ?)'
		);
		$ins->execute([$scope, $identifier, $now->format('Y-m-d H:i:s')]);
		return;
	}

	$rowStart = new DateTimeImmutable($row['window_start']);
	if ($rowStart < $windowStart) {
		$upd = $db->prepare(
			'UPDATE provision_rate_limits SET hits = 1, window_start = ? WHERE id = ?'
		);
		$upd->execute([$now->format('Y-m-d H:i:s'), $row['id']]);
		return;
	}

	if ((int) $row['hits'] >= $maxHits) {
		throw new RuntimeException('Trop de tentatives. Réessayez plus tard.');
	}

	$upd = $db->prepare('UPDATE provision_rate_limits SET hits = hits + 1 WHERE id = ?');
	$upd->execute([$row['id']]);
}
