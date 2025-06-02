"""initial migration

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2023-06-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create slack_users table
    op.create_table(
        'slack_users',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('name', sa.String(255)),
        sa.Column('real_name', sa.String(255)),
        sa.Column('display_name', sa.String(255)),
        sa.Column('email', sa.String(255), unique=True),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('is_owner', sa.Boolean(), default=False),
        sa.Column('is_bot', sa.Boolean(), default=False),
        sa.Column('deleted', sa.Boolean(), default=False),
        sa.Column('team_id', sa.String(255)),
        sa.Column('data', JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create index on email
    op.create_index('idx_slack_users_email', 'slack_users', ['email'])
    
    # Create slack_channels table
    op.create_table(
        'slack_channels',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('name', sa.String(255)),
        sa.Column('is_private', sa.Boolean(), default=False),
        sa.Column('is_archived', sa.Boolean(), default=False),
        sa.Column('created', sa.DateTime(timezone=True)),
        sa.Column('creator', sa.String(255)),
        sa.Column('num_members', sa.Integer(), default=0),
        sa.Column('purpose', sa.Text()),
        sa.Column('topic', sa.Text()),
        sa.Column('data', JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create index on channel name
    op.create_index('idx_slack_channels_name', 'slack_channels', ['name'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('slack_channels')
    op.drop_table('slack_users') 