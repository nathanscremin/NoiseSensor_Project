-- NoiseSensor
-- Migration 004: normalização/reparo do schema do sistema de administração
--
-- Estado esperado antes desta migration:
--   * users.role pode já existir (neste banco já existe)
--   * sensors.user_id já foi removido
--   * sensor_users já existe e contém os vínculos N:N migrados
--   * admin_audit_log já existe
--
-- Esta migration foi feita para o estado REAL atualmente identificado no banco:
--   users = 3
--   sensors = 4
--   sensor_users = 4
--   admin_audit_log = 0
--
-- Objetivo:
--   * não apagar usuários, sensores, leituras, previsões, alertas ou sessões;
--   * não recriar tabelas que já estão corretas;
--   * completar apenas estrutura/índices/constraints ausentes;
--   * validar integridade antes de criar PK/FK;
--   * manter tudo transacional.
--
-- IMPORTANTE:
--   Execute com a aplicação parada.
--   Se alguma validação encontrar dados incompatíveis, a migration aborta
--   antes do COMMIT e o PostgreSQL desfaz as alterações desta transação.

BEGIN;

-- ============================================================
-- 1. USERS.ROLE
-- ============================================================

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role VARCHAR(20);

UPDATE users
SET role = 'user'
WHERE role IS NULL;

ALTER TABLE users
    ALTER COLUMN role SET DEFAULT 'user';

ALTER TABLE users
    ALTER COLUMN role SET NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM users
        WHERE role NOT IN ('user', 'admin')
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: users.role possui valores inválidos.';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.users'::regclass
          AND conname = 'chk_users_role'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT chk_users_role
            CHECK (role IN ('user', 'admin'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_users_role
    ON users(role);


-- ============================================================
-- 2. SENSOR_USERS — RELAÇÃO N:N
-- ============================================================

CREATE TABLE IF NOT EXISTS sensor_users (
    sensor_id BIGINT,
    user_id BIGINT,
    assigned_at TIMESTAMPTZ
);

-- Completa a estrutura caso a tabela tenha sido criada parcialmente.

ALTER TABLE sensor_users
    ADD COLUMN IF NOT EXISTS sensor_id BIGINT;

ALTER TABLE sensor_users
    ADD COLUMN IF NOT EXISTS user_id BIGINT;

ALTER TABLE sensor_users
    ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ;

UPDATE sensor_users
SET assigned_at = NOW()
WHERE assigned_at IS NULL;

ALTER TABLE sensor_users
    ALTER COLUMN sensor_id SET NOT NULL;

ALTER TABLE sensor_users
    ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE sensor_users
    ALTER COLUMN assigned_at SET DEFAULT NOW();

ALTER TABLE sensor_users
    ALTER COLUMN assigned_at SET NOT NULL;


-- Antes de criar a chave primária, garante que não existem
-- associações duplicadas.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sensor_users
        GROUP BY sensor_id, user_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: existem associações duplicadas em sensor_users.';
    END IF;
END
$$;


-- Antes de criar as FKs, garante que não existem registros órfãos.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sensor_users su
        LEFT JOIN sensors s
            ON s.sensor_id = su.sensor_id
        WHERE s.sensor_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: existem sensor_users com sensor_id inexistente.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM sensor_users su
        LEFT JOIN users u
            ON u.user_id = su.user_id
        WHERE u.user_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: existem sensor_users com user_id inexistente.';
    END IF;
END
$$;


-- PK N:N.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.sensor_users'::regclass
          AND contype = 'p'
    ) THEN
        ALTER TABLE sensor_users
            ADD CONSTRAINT pk_sensor_users
            PRIMARY KEY (sensor_id, user_id);
    END IF;
END
$$;


-- FK para sensors.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = ANY(c.conkey)
        JOIN pg_class r
          ON r.oid = c.confrelid
        WHERE c.conrelid = 'public.sensor_users'::regclass
          AND c.contype = 'f'
          AND a.attname = 'sensor_id'
          AND r.oid = 'public.sensors'::regclass
    ) THEN
        ALTER TABLE sensor_users
            ADD CONSTRAINT fk_sensor_users_sensor
            FOREIGN KEY (sensor_id)
            REFERENCES sensors(sensor_id)
            ON DELETE CASCADE;
    END IF;
END
$$;


-- FK para users.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = ANY(c.conkey)
        JOIN pg_class r
          ON r.oid = c.confrelid
        WHERE c.conrelid = 'public.sensor_users'::regclass
          AND c.contype = 'f'
          AND a.attname = 'user_id'
          AND r.oid = 'public.users'::regclass
    ) THEN
        ALTER TABLE sensor_users
            ADD CONSTRAINT fk_sensor_users_user
            FOREIGN KEY (user_id)
            REFERENCES users(user_id)
            ON DELETE CASCADE;
    END IF;
END
$$;


CREATE INDEX IF NOT EXISTS idx_sensor_users_user_id
    ON sensor_users(user_id);

CREATE INDEX IF NOT EXISTS idx_sensor_users_sensor_id
    ON sensor_users(sensor_id);


-- ============================================================
-- 3. ADMIN_AUDIT_LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id BIGINT GENERATED BY DEFAULT AS IDENTITY,
    admin_user_id BIGINT,
    action VARCHAR(50),
    target_user_id BIGINT,
    target_sensor_id BIGINT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Completa estrutura caso a tabela exista de forma parcial.

ALTER TABLE admin_audit_log
    ADD COLUMN IF NOT EXISTS audit_id BIGINT GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE admin_audit_log
    ADD COLUMN IF NOT EXISTS admin_user_id BIGINT;

ALTER TABLE admin_audit_log
    ADD COLUMN IF NOT EXISTS action VARCHAR(50);

ALTER TABLE admin_audit_log
    ADD COLUMN IF NOT EXISTS target_user_id BIGINT;

ALTER TABLE admin_audit_log
    ADD COLUMN IF NOT EXISTS target_sensor_id BIGINT;

ALTER TABLE admin_audit_log
    ADD COLUMN IF NOT EXISTS details TEXT;

ALTER TABLE admin_audit_log
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

UPDATE admin_audit_log
SET created_at = NOW()
WHERE created_at IS NULL;


-- Não pode haver IDs duplicados ou nulos antes da PK.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM admin_audit_log
        GROUP BY audit_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: audit_id duplicado em admin_audit_log.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM admin_audit_log
        WHERE audit_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: audit_id nulo em admin_audit_log.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM admin_audit_log
        WHERE admin_user_id IS NULL
           OR action IS NULL
           OR details IS NULL
           OR created_at IS NULL
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: campos obrigatórios nulos em admin_audit_log.';
    END IF;
END
$$;


ALTER TABLE admin_audit_log
    ALTER COLUMN admin_user_id SET NOT NULL;

ALTER TABLE admin_audit_log
    ALTER COLUMN action SET NOT NULL;

ALTER TABLE admin_audit_log
    ALTER COLUMN details SET NOT NULL;

ALTER TABLE admin_audit_log
    ALTER COLUMN created_at SET DEFAULT NOW();

ALTER TABLE admin_audit_log
    ALTER COLUMN created_at SET NOT NULL;


-- PK da auditoria.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.admin_audit_log'::regclass
          AND contype = 'p'
    ) THEN
        ALTER TABLE admin_audit_log
            ADD CONSTRAINT admin_audit_log_pkey
            PRIMARY KEY (audit_id);
    END IF;
END
$$;


-- FK do administrador.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = ANY(c.conkey)
        JOIN pg_class r
          ON r.oid = c.confrelid
        WHERE c.conrelid = 'public.admin_audit_log'::regclass
          AND c.contype = 'f'
          AND a.attname = 'admin_user_id'
          AND r.oid = 'public.users'::regclass
    ) THEN
        ALTER TABLE admin_audit_log
            ADD CONSTRAINT fk_admin_audit_admin
            FOREIGN KEY (admin_user_id)
            REFERENCES users(user_id)
            ON DELETE RESTRICT;
    END IF;
END
$$;


-- FK do usuário alvo.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = ANY(c.conkey)
        JOIN pg_class r
          ON r.oid = c.confrelid
        WHERE c.conrelid = 'public.admin_audit_log'::regclass
          AND c.contype = 'f'
          AND a.attname = 'target_user_id'
          AND r.oid = 'public.users'::regclass
    ) THEN
        ALTER TABLE admin_audit_log
            ADD CONSTRAINT fk_admin_audit_target_user
            FOREIGN KEY (target_user_id)
            REFERENCES users(user_id)
            ON DELETE SET NULL;
    END IF;
END
$$;


-- FK do sensor alvo.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = ANY(c.conkey)
        JOIN pg_class r
          ON r.oid = c.confrelid
        WHERE c.conrelid = 'public.admin_audit_log'::regclass
          AND c.contype = 'f'
          AND a.attname = 'target_sensor_id'
          AND r.oid = 'public.sensors'::regclass
    ) THEN
        ALTER TABLE admin_audit_log
            ADD CONSTRAINT fk_admin_audit_target_sensor
            FOREIGN KEY (target_sensor_id)
            REFERENCES sensors(sensor_id)
            ON DELETE SET NULL;
    END IF;
END
$$;


CREATE INDEX IF NOT EXISTS idx_admin_audit_created_at
    ON admin_audit_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_audit_target_user
    ON admin_audit_log(target_user_id);

CREATE INDEX IF NOT EXISTS idx_admin_audit_target_sensor
    ON admin_audit_log(target_sensor_id);


-- ============================================================
-- 4. VALIDAÇÃO FINAL DA ESTRUTURA ADMINISTRATIVA
-- ============================================================

DO $$
BEGIN
    -- role
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'role'
    ) THEN
        RAISE EXCEPTION 'Migration 004 abortada: users.role não existe.';
    END IF;

    -- sensor_users
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'sensor_users'
    ) THEN
        RAISE EXCEPTION 'Migration 004 abortada: sensor_users não existe.';
    END IF;

    -- audit
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'admin_audit_log'
    ) THEN
        RAISE EXCEPTION 'Migration 004 abortada: admin_audit_log não existe.';
    END IF;

    -- A coluna antiga não deve voltar a existir.
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sensors'
          AND column_name = 'user_id'
    ) THEN
        RAISE EXCEPTION
            'Migration 004 abortada: sensors.user_id ainda existe. Não recriaremos a relação antiga.';
    END IF;
END
$$;


COMMIT;


-- ============================================================
-- 5. CONFERÊNCIA PÓS-MIGRATION
-- ============================================================
--
-- Execute manualmente estas consultas depois do COMMIT, caso queira
-- conferir o resultado:
--
-- SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY role;
--
-- SELECT
--     su.sensor_id,
--     s.name AS sensor_name,
--     su.user_id,
--     u.name AS user_name
-- FROM sensor_users su
-- JOIN sensors s ON s.sensor_id = su.sensor_id
-- JOIN users u ON u.user_id = su.user_id
-- ORDER BY su.sensor_id, su.user_id;
--
-- SELECT COUNT(*) FROM admin_audit_log;
--
-- SELECT EXISTS (
--     SELECT 1
--     FROM information_schema.columns
--     WHERE table_schema = 'public'
--       AND table_name = 'sensors'
--       AND column_name = 'user_id'
-- ) AS old_sensor_user_column_exists;
