"""Initial Slack tables for slack database

Revision ID: slack_001
Revises: 
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'slack_001'
down_revision = None  # This is the base migration for slack database
branch_labels = ('slack',)  # This migration belongs to the slack branch
depends_on = None


def upgrade() -> None:
    # Create slack_users table
    op.create_table('slack_users',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('real_name', sa.String(255), nullable=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('is_owner', sa.Boolean(), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=True),
        sa.Column('deleted', sa.Boolean(), nullable=True),
        sa.Column('team_id', sa.String(255), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create slack_channels table
    op.create_table('slack_channels',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_private', sa.Boolean(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=True),
        sa.Column('creator', sa.String(255), nullable=True),
        sa.Column('num_members', sa.Integer(), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('topic', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_slack_users_email', 'slack_users', ['email'])
    op.create_index('idx_slack_channels_name', 'slack_channels', ['name'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_slack_channels_name', table_name='slack_channels')
    op.drop_index('idx_slack_users_email', table_name='slack_users')
    
    # Drop tables
    op.drop_table('slack_channels')
    op.drop_table('slack_users') 