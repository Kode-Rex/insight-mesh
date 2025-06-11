"""
Domain models for InsightMesh.

This module contains the core domain models that represent the business logic
and relationships between entities in the system.
"""

from .person import Person
from .channels import Channel
from .messages import Message

__all__ = ['Person', 'Channel', 'Message'] 