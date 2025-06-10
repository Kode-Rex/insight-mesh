"""rename_mcp_users_to_insightmesh_users

Revision ID: b84d0f93c3ce
Revises: insightmesh_001
Create Date: 2025-06-10 17:18:32.801193

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b84d0f93c3ce'
down_revision = 'insightmesh_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, drop foreign key constraints that reference mcp_users
    op.drop_constraint('contexts_user_id_fkey', 'contexts', type_='foreignkey')
    op.drop_constraint('conversations_user_id_fkey', 'conversations', type_='foreignkey')
    
    # Rename the table
    op.rename_table('mcp_users', 'insightmesh_users')
    
    # Recreate foreign key constraints with new table name
    op.create_foreign_key('contexts_user_id_fkey', 'contexts', 'insightmesh_users', ['user_id'], ['id'])
    op.create_foreign_key('conversations_user_id_fkey', 'conversations', 'insightmesh_users', ['user_id'], ['id'])


def downgrade() -> None:
    # Drop foreign key constraints
    op.drop_constraint('contexts_user_id_fkey', 'contexts', type_='foreignkey')
    op.drop_constraint('conversations_user_id_fkey', 'conversations', type_='foreignkey')
    
    # Rename the table back
    op.rename_table('insightmesh_users', 'mcp_users')
    
    # Recreate foreign key constraints with original table name
    op.create_foreign_key('contexts_user_id_fkey', 'contexts', 'mcp_users', ['user_id'], ['id'])
    op.create_foreign_key('conversations_user_id_fkey', 'conversations', 'mcp_users', ['user_id'], ['id']) 