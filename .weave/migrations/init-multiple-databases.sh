#!/bin/bash
set -e

# Create multiple databases for different services
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create databases for different services
    CREATE DATABASE openwebui;
    CREATE DATABASE litellm;
    CREATE DATABASE mcp;
    CREATE DATABASE insight_mesh;
    
    -- Grant all privileges to the postgres user on all databases
    GRANT ALL PRIVILEGES ON DATABASE openwebui TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE litellm TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE mcp TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE insight_mesh TO $POSTGRES_USER;
    
    -- Connect to insight_mesh database and create Slack tables
    \c insight_mesh;
    
    -- Create slack_users table
    CREATE TABLE IF NOT EXISTS slack_users (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255),
        real_name VARCHAR(255),
        display_name VARCHAR(255),
        email VARCHAR(255) UNIQUE,
        is_admin BOOLEAN DEFAULT FALSE,
        is_owner BOOLEAN DEFAULT FALSE,
        is_bot BOOLEAN DEFAULT FALSE,
        deleted BOOLEAN DEFAULT FALSE,
        team_id VARCHAR(255),
        data JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create index on email for faster lookups
    CREATE INDEX IF NOT EXISTS idx_slack_users_email ON slack_users(email);
    
    -- Create slack_channels table
    CREATE TABLE IF NOT EXISTS slack_channels (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255),
        is_private BOOLEAN DEFAULT FALSE,
        is_archived BOOLEAN DEFAULT FALSE,
        created TIMESTAMP WITH TIME ZONE,
        creator VARCHAR(255),
        num_members INTEGER DEFAULT 0,
        purpose TEXT,
        topic TEXT,
        data JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create index on channel name
    CREATE INDEX IF NOT EXISTS idx_slack_channels_name ON slack_channels(name);
    
    -- Connect to mcp database and create MCP tables
    \c mcp;
    
    -- Create mcp_users table
    CREATE TABLE IF NOT EXISTS mcp_users (
        id VARCHAR PRIMARY KEY,
        email VARCHAR UNIQUE,
        name VARCHAR,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        is_active BOOLEAN DEFAULT TRUE,
        metadata JSONB DEFAULT '{}',
        openwebui_id VARCHAR
    );
    
    -- Create contexts table
    CREATE TABLE IF NOT EXISTS contexts (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR REFERENCES mcp_users(id),
        content JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        expires_at TIMESTAMP WITH TIME ZONE,
        is_active BOOLEAN DEFAULT TRUE,
        metadata JSONB DEFAULT '{}'
    );
    
    -- Create conversations table
    CREATE TABLE IF NOT EXISTS conversations (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR REFERENCES mcp_users(id),
        title VARCHAR,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        is_active BOOLEAN DEFAULT TRUE,
        metadata JSONB DEFAULT '{}'
    );
    
    -- Create messages table
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        conversation_id INTEGER REFERENCES conversations(id),
        role VARCHAR,
        content TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        metadata JSONB DEFAULT '{}'
    );
    
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_contexts_user_id ON contexts(user_id);
    CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at);
    CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
    
EOSQL

echo "Multiple databases created successfully!" 