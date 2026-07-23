-- Accusés chat Asaphone (client_id + read_at)
-- Appliquer via : sudo bash scripts/apply-chat-status-schema.sh

ALTER TABLE provision_chat_messages
	ADD COLUMN IF NOT EXISTS client_id VARCHAR(64) NULL DEFAULT NULL AFTER body,
	ADD COLUMN IF NOT EXISTS read_at DATETIME NULL DEFAULT NULL AFTER delivered_at;

ALTER TABLE provision_chat_messages
	ADD INDEX IF NOT EXISTS idx_chat_from_client (from_ext, client_id),
	ADD INDEX IF NOT EXISTS idx_chat_from_id (from_ext, id);
