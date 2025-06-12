"""
Synchronization utilities for multi-store models.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session
from typing import Type, Any
import logging

logger = logging.getLogger(__name__)


class SyncMixin:
    """Mixin to automatically sync changes across stores."""
    
    @classmethod
    def enable_auto_sync(cls):
        """Enable automatic synchronization on SQLAlchemy events."""
        
        @event.listens_for(cls, 'after_insert')
        def after_insert(mapper, connection, target):
            """Sync to other stores after insert."""
            cls._sync_after_change(target, 'insert')
        
        @event.listens_for(cls, 'after_update')
        def after_update(mapper, connection, target):
            """Sync to other stores after update."""
            cls._sync_after_change(target, 'update')
        
        @event.listens_for(cls, 'after_delete')
        def after_delete(mapper, connection, target):
            """Sync to other stores after delete."""
            cls._sync_after_change(target, 'delete')
    
    @classmethod
    def _sync_after_change(cls, instance, operation: str):
        """Sync instance to other stores after a change."""
        try:
            if operation == 'delete':
                # Delete from other stores
                if hasattr(instance, 'delete_from_elasticsearch'):
                    instance.delete_from_elasticsearch()
                # Note: Neo4j deletion would need custom logic based on relationships
            else:
                # Insert/Update in other stores
                if hasattr(instance, 'sync_to_neo4j'):
                    instance.sync_to_neo4j()
                    if hasattr(instance, 'sync_relationships_to_neo4j'):
                        instance.sync_relationships_to_neo4j()
                
                if hasattr(instance, 'sync_to_elasticsearch'):
                    instance.sync_to_elasticsearch()
        
        except Exception as e:
            logger.error(f"Error syncing {cls.__name__} after {operation}: {e}")
            # Don't raise - we don't want to break the main transaction
    
    def sync_all_stores(self):
        """Manually sync this instance to all configured stores."""
        if hasattr(self, 'sync_to_neo4j'):
            self.sync_to_neo4j()
            if hasattr(self, 'sync_relationships_to_neo4j'):
                self.sync_relationships_to_neo4j()
        
        if hasattr(self, 'sync_to_elasticsearch'):
            self.sync_to_elasticsearch()


def enable_auto_sync_for_model(model_class: Type):
    """Enable auto-sync for a specific model class."""
    if hasattr(model_class, 'enable_auto_sync'):
        model_class.enable_auto_sync()
    else:
        # Add SyncMixin methods if not already present
        for attr_name in dir(SyncMixin):
            if not attr_name.startswith('_') or attr_name == '_sync_after_change':
                setattr(model_class, attr_name, getattr(SyncMixin, attr_name))
        model_class.enable_auto_sync()


def bulk_sync_to_stores(session: Session, model_class: Type, **filters):
    """Bulk sync existing records to other stores."""
    query = session.query(model_class)
    
    # Apply filters if provided
    for field, value in filters.items():
        if hasattr(model_class, field):
            query = query.filter(getattr(model_class, field) == value)
    
    count = 0
    for instance in query:
        try:
            instance.sync_all_stores()
            count += 1
            if count % 100 == 0:
                logger.info(f"Synced {count} {model_class.__name__} records")
        except Exception as e:
            logger.error(f"Error syncing {model_class.__name__} {instance.id}: {e}")
    
    logger.info(f"Completed bulk sync of {count} {model_class.__name__} records") 