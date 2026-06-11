-- Tables provisionnement Asaphone (base asterisk)
-- Appliquer : sudo mysql asterisk < provision-schema.sql

CREATE TABLE IF NOT EXISTS provision_requests (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    email_verified TINYINT(1) NOT NULL DEFAULT 0,
    verify_code_hash VARCHAR(255) DEFAULT NULL,
    verify_expires DATETIME DEFAULT NULL,
    extension VARCHAR(20) DEFAULT NULL,
    status ENUM(
        'pending',
        'verified',
        'pending_admin',
        'provisioned',
        'revoked'
    ) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_provision_email (email),
    KEY idx_provision_status (status),
    KEY idx_provision_extension (extension)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS provision_tokens (
    jti VARCHAR(36) NOT NULL,
    extension VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    claim_token VARCHAR(64) NOT NULL,
    payload_enc TEXT DEFAULT NULL,
    expires DATETIME NOT NULL,
    used TINYINT(1) NOT NULL DEFAULT 0,
    used_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (jti),
    UNIQUE KEY uq_claim_token (claim_token),
    KEY idx_provision_tokens_email (email),
    KEY idx_provision_tokens_ext (extension),
    KEY idx_provision_tokens_expires (expires)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS provision_rate_limits (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    scope VARCHAR(64) NOT NULL,
    identifier VARCHAR(255) NOT NULL,
    hits INT UNSIGNED NOT NULL DEFAULT 1,
    window_start DATETIME NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_rate_scope_id (scope, identifier),
    KEY idx_rate_window (window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
