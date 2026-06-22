-- Peers WireGuard auto-provisionnés (API /provision/api/v1/vpn/*)
-- Appliquer : sudo mysql asterisk < scripts/provision-schema-vpn.sql

CREATE TABLE IF NOT EXISTS provision_vpn_peers (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    extension VARCHAR(20) DEFAULT NULL,
    tunnel_ip VARCHAR(15) NOT NULL,
    client_public_key VARCHAR(64) DEFAULT NULL,
    client_private_key_enc TEXT DEFAULT NULL,
    claim_token VARCHAR(64) DEFAULT NULL,
    claim_expires DATETIME DEFAULT NULL,
    verify_code_hash VARCHAR(255) DEFAULT NULL,
    verify_expires DATETIME DEFAULT NULL,
    status ENUM('pending', 'ready', 'active', 'revoked') NOT NULL DEFAULT 'pending',
    claimed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vpn_email (email),
    UNIQUE KEY uq_vpn_tunnel_ip (tunnel_ip),
    UNIQUE KEY uq_vpn_client_pubkey (client_public_key),
    UNIQUE KEY uq_vpn_claim_token (claim_token),
    KEY idx_vpn_status (status),
    KEY idx_vpn_extension (extension)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
