-- Messagerie vocale Asaphone (notifications sans e-mail WAV)
-- Appliquer : sudo mysql asterisk < scripts/provision-schema-voicemail.sql

ALTER TABLE provision_requests
    ADD COLUMN phone VARCHAR(32) DEFAULT NULL AFTER email;

CREATE TABLE IF NOT EXISTS provision_vm_notifications (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    extension VARCHAR(20) NOT NULL,
    email VARCHAR(255) DEFAULT NULL,
    phone VARCHAR(32) DEFAULT NULL,
    caller_id VARCHAR(80) DEFAULT NULL,
    duration INT UNSIGNED NOT NULL DEFAULT 0,
    msg_id VARCHAR(64) DEFAULT NULL,
    msg_path VARCHAR(512) DEFAULT NULL,
    notify_token VARCHAR(64) NOT NULL,
    expires DATETIME NOT NULL,
    consumed TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vm_notify_token (notify_token),
    KEY idx_vm_notify_ext (extension),
    KEY idx_vm_notify_expires (expires)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
