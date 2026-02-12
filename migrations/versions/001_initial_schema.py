"""Initial schema with pgvector extension

Revision ID: 001
Revises: 
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_customers_email', 'customers', ['email'])
    
    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('merchant', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_customer_id', 'transactions', ['customer_id'])
    op.create_index('ix_transactions_timestamp', 'transactions', ['timestamp'])
    
    # Create policy_documents table
    op.create_table(
        'policy_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_policy_documents_category', 'policy_documents', ['category'])
    # Create vector similarity index using HNSW (Hierarchical Navigable Small World)
    op.execute(
        'CREATE INDEX ix_policy_documents_embedding_hnsw ON policy_documents '
        'USING hnsw (embedding vector_cosine_ops)'
    )
    
    # Create workflow_runs table
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('input_params', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_runs_customer_id', 'workflow_runs', ['customer_id'])
    op.create_index('ix_workflow_runs_status', 'workflow_runs', ['status'])
    op.create_index('ix_workflow_runs_created_at', 'workflow_runs', ['created_at'])
    
    # Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_run_id', sa.UUID(), nullable=False),
        sa.Column('node_name', sa.String(length=100), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=True),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('output_data', sa.JSON(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_events_workflow_run_id', 'audit_events', ['workflow_run_id'])
    op.create_index('ix_audit_events_node_name', 'audit_events', ['node_name'])
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_audit_events_timestamp', table_name='audit_events')
    op.drop_index('ix_audit_events_node_name', table_name='audit_events')
    op.drop_index('ix_audit_events_workflow_run_id', table_name='audit_events')
    op.drop_table('audit_events')
    
    op.drop_index('ix_workflow_runs_created_at', table_name='workflow_runs')
    op.drop_index('ix_workflow_runs_status', table_name='workflow_runs')
    op.drop_index('ix_workflow_runs_customer_id', table_name='workflow_runs')
    op.drop_table('workflow_runs')
    
    op.execute('DROP INDEX IF EXISTS ix_policy_documents_embedding_hnsw')
    op.drop_index('ix_policy_documents_category', table_name='policy_documents')
    op.drop_table('policy_documents')
    
    op.drop_index('ix_transactions_timestamp', table_name='transactions')
    op.drop_index('ix_transactions_customer_id', table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_index('ix_customers_email', table_name='customers')
    op.drop_table('customers')
    
    op.execute('DROP EXTENSION IF EXISTS vector')
