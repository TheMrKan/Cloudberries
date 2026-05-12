"""Populate service_type table with initial data."""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Insert initial service type data."""
    service_type_table = sa.table(
        'service_type',
        sa.column('type_id', sa.String),
        sa.column('name', sa.String),
        sa.column('description', sa.String),
        sa.column('parameters', sa.JSON),
    )

    op.bulk_insert(
        service_type_table,
        [
            {
                'type_id': 'compute',
                'name': 'Compute',
                'description': 'Virtual CPU computing resources',
                'parameters': {'vcpu': {'name': 'vCPU', 'uom': 'шт'}}
            },
            {
                'type_id': 'memory',
                'name': 'Memory',
                'description': 'RAM memory resources',
                'parameters': {'ram': {'name': 'RAM', 'uom': 'ГБ'}}
            },
            {
                'type_id': 'storage',
                'name': 'Storage',
                'description': 'Disk storage resources',
                'parameters': {'disk': {'name': 'Disk storage', 'uom': 'ГБ'}}
            },
            {
                'type_id': 'network',
                'name': 'Network',
                'description': 'Network bandwidth resources',
                'parameters': {'bandwidth': {'name': 'Bandwidth', 'uom': 'Мбит/с'}}
            },
            {
                'type_id': 'load_balancer',
                'name': 'Load Balancer',
                'description': 'Load balancing service',
                'parameters': {'lb': {'name': 'Load Balancer', 'uom': 'шт'}}
            },
            {
                'type_id': 'kubernetes',
                'name': 'Kubernetes',
                'description': 'Managed Kubernetes service',
                'parameters': {'k8s': {'name': 'Kubernetes cluster', 'uom': 'шт'}}
            },
            {
                'type_id': 'database',
                'name': 'Database',
                'description': 'Managed database service',
                'parameters': {'db': {'name': 'Database instance', 'uom': 'шт'}}
            },
            {
                'type_id': 'other',
                'name': 'Other',
                'description': 'Other miscellaneous services',
                'parameters': {}
            }
        ]
    )


def downgrade():
    """Remove initial service type data."""
    op.execute("DELETE FROM service_type WHERE type_id IN ('compute', 'memory', 'storage', 'network', 'load_balancer', 'kubernetes', 'database', 'other')")