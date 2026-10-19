-- ==============================================================================
-- Least-Privilege Debezium CDC User Initialization for MySQL 8.0
-- ==============================================================================

CREATE USER IF NOT EXISTS 'debezium_user'@'%' IDENTIFIED BY 'debezium_cdc_secret_2026';

-- Debezium requires SELECT on tracked databases, plus replication grants
GRANT SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'debezium_user'@'%';

FLUSH PRIVILEGES;
