-- Messages chat Asaphone (file d'attente si destinataire offline)
-- Appliquer : sudo mysql asterisk < scripts/provision-schema-chat.sql

CREATE TABLE IF NOT EXISTS provision_chat_messages (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    from_ext VARCHAR(20) NOT NULL,
    to_ext VARCHAR(20) NOT NULL,
    body TEXT NOT NULL,
    client_id VARCHAR(64) NULL DEFAULT NULL,
    sip_delivered TINYINT(1) NOT NULL DEFAULT 0,
    consumed TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at DATETIME DEFAULT NULL,
    read_at DATETIME DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_chat_to_pending (to_ext, consumed, sip_delivered),
    KEY idx_chat_created (created_at),
    KEY idx_chat_from_client (from_ext, client_id),
    KEY idx_chat_from_id (from_ext, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
