-- Groupes messagerie Asaphone + salles ConfBridge
-- sudo mysql asterisk < scripts/provision-schema-groups.sql

CREATE TABLE IF NOT EXISTS provision_chat_groups (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    group_id VARCHAR(64) NOT NULL,
    owner_ext VARCHAR(20) NOT NULL,
    title VARCHAR(120) NOT NULL DEFAULT '',
    room VARCHAR(64) NOT NULL,
    call_uri VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_group_id (group_id),
    UNIQUE KEY uk_room (room),
    KEY idx_owner (owner_ext)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS provision_chat_group_members (
    group_id VARCHAR(64) NOT NULL,
    member_ext VARCHAR(20) NOT NULL,
    PRIMARY KEY (group_id, member_ext),
    KEY idx_member (member_ext)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
