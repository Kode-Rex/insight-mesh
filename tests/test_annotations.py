"""
Tests for the Weave multi-store annotation system.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from domain.data.slack import SlackUser, SlackChannel, SlackBase


class TestWeaveAnnotations:
    """Test the Weave annotation system functionality."""
    
    def setup_method(self):
        """Set up test database."""
        # Use in-memory SQLite for testing
        self.engine = create_engine("sqlite:///:memory:")
        SlackBase.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.session.close()
    
    def test_model_has_annotations(self):
        """Test that models have the annotation configurations."""
        # Check Neo4j configuration
        assert hasattr(SlackUser, '_neo4j_node_config')
        assert SlackUser._neo4j_node_config.label == "SlackUser"
        assert SlackUser._neo4j_node_config.id_field == 'id'
        
        # Check Elasticsearch configuration
        assert hasattr(SlackUser, '_elasticsearch_config')
        assert SlackUser._elasticsearch_config.index_name == "slack_users"
        assert 'name' in SlackUser._elasticsearch_config.text_fields
    
    def test_model_has_mixin_methods(self):
        """Test that models have the mixin methods."""
        user = SlackUser(
            id="U123",
            name="test_user",
            email="test@example.com"
        )
        
        # Check Neo4j methods
        assert hasattr(user, 'sync_to_neo4j')
        assert hasattr(user, 'sync_relationships_to_neo4j')
        assert hasattr(user, 'find_in_neo4j')
        
        # Check Elasticsearch methods
        assert hasattr(user, 'sync_to_elasticsearch')
        assert hasattr(user, 'search_elasticsearch')
        assert hasattr(user, 'create_elasticsearch_index')
        
        # Check sync methods
        assert hasattr(user, 'sync_all_stores')
    
    def test_neo4j_properties_extraction(self):
        """Test Neo4j property extraction."""
        user = SlackUser(
            id="U123",
            name="test_user",
            real_name="Test User",
            email="test@example.com",
            is_admin=False,
            is_bot=False
        )
        
        properties = user._get_neo4j_properties()
        
        # Should include most fields
        assert properties['id'] == "U123"
        assert properties['name'] == "test_user"
        assert properties['email'] == "test@example.com"
        
        # Should exclude configured fields
        assert 'data' not in properties
        assert 'created_at' not in properties
    
    def test_elasticsearch_document_extraction(self):
        """Test Elasticsearch document extraction."""
        user = SlackUser(
            id="U123",
            name="test_user",
            real_name="Test User",
            email="test@example.com"
        )
        
        document = user._get_elasticsearch_document()
        
        # Should include most fields
        assert document['id'] == "U123"
        assert document['name'] == "test_user"
        assert document['email'] == "test@example.com"
        
        # Should exclude configured fields
        assert 'data' not in document
    
    @patch('weave.bin.modules.annotations.graph.GraphDatabase.driver')
    def test_neo4j_sync(self, mock_driver):
        """Test Neo4j synchronization."""
        mock_session = Mock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
        
        user = SlackUser(
            id="U123",
            name="test_user",
            email="test@example.com"
        )
        
        user.sync_to_neo4j()
        
        # Verify Neo4j query was called
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "MERGE (n:SlackUser" in call_args[0][0]
        assert call_args[1]['id'] == "U123"
    
    @patch('weave.bin.modules.annotations.search.Elasticsearch')
    def test_elasticsearch_sync(self, mock_es_class):
        """Test Elasticsearch synchronization."""
        mock_es = Mock()
        mock_es_class.return_value = mock_es
        
        user = SlackUser(
            id="U123",
            name="test_user",
            email="test@example.com"
        )
        
        user.sync_to_elasticsearch()
        
        # Verify Elasticsearch index was called
        mock_es.index.assert_called_once()
        call_args = mock_es.index.call_args
        assert call_args[1]['index'] == "slack_users"
        assert call_args[1]['id'] == "U123"
    
    def test_business_logic_preserved(self):
        """Test that business logic methods still work."""
        user = SlackUser(
            id="U123",
            name="test_user",
            display_name="Test User",
            is_bot=False,
            deleted=False
        )
        
        # Test custom business logic methods
        assert user.display_name_or_name == "Test User"
        assert user.is_active_user() == True
        
        # Test with bot user
        bot_user = SlackUser(
            id="B123",
            name="bot_user",
            is_bot=True,
            deleted=False
        )
        assert bot_user.is_active_user() == False
    
    def test_channel_relationships(self):
        """Test that channel relationships are configured."""
        assert hasattr(SlackChannel, '_neo4j_relationships')
        relationships = SlackChannel._neo4j_relationships
        assert len(relationships) > 0
        
        rel = relationships[0]
        assert rel.type == "CREATED_BY"
        assert rel.source_field == "creator"


if __name__ == "__main__":
    pytest.main([__file__]) 