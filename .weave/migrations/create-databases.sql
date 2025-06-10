-- Create databases for different services
-- This script only creates the databases; table creation is handled by Alembic migrations

-- Create databases if they don't exist
SELECT 'CREATE DATABASE openwebui' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'openwebui')\gexec
SELECT 'CREATE DATABASE litellm' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'litellm')\gexec
SELECT 'CREATE DATABASE mcp' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mcp')\gexec
SELECT 'CREATE DATABASE insight_mesh' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'insight_mesh')\gexec 