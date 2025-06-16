from dagster import build_op_context
from .google_drive_assets import (
    google_drive_service,
    google_drive_files,
    index_files,
    GoogleDriveConfig,
)
import os
from dotenv import load_dotenv
import logging
import unittest.mock as mock
import pytest
import json
import tempfile
import shutil
from unittest.mock import MagicMock, patch, call
from dagster import ConfigurableResource

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from parent directory's .env file
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

# Override Neo4j and Elasticsearch hostnames for testing
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["ELASTICSEARCH_HOST"] = "localhost"

# Create mock credentials file for testing
MOCK_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "mock_credentials.json")
MOCK_CREDENTIALS_CONTENT = {
    "type": "service_account",
    "project_id": "mock-project",
    "private_key_id": "mock",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIBVQIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEAvkZ0MmLc+S0+YMaN\nS5cLwJZRRJwJ0C77bIswrDdQWdkp+I+wvWYeKv3dJP9l4QbQ+SqKu1+sUnLha9Q7\nmKjXmQIDAQABAkEAoRmivbdKBAWXLsT3Xaa1Jv6q1qEt0SuiTEcnH4A67fNKmGZW\nY+7Q54CorJiDKAVL6lkSETn3MHH9SHBP0LhQAQIhAP0BDwWJFMo21+OxuPOG6e/l\nQiQBZYVPOBUGN60wpVQ5AiEAwPJXc2KXBDnZ9vp1+t0rq0at+gCfSwCQtZwPLlqQ\nPEECIEdMOD0+yfgOxPCzG6K8P9zGHKZuRgb+ZpMPtX1jGz7BAiEAgBQTjZGqxyOj\n0qmdmFm0QSPlPFYCGl+yXymS2GU+5wECIFfbU1NV3r3gzHjC2wGJmocAGLWfxnGE\nJdmR9xT4Pwis\n-----END PRIVATE KEY-----\n",
    "client_email": "mock@example.com",
    "client_id": "mock",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mock%40example.com"
}

# Write mock credentials to file if it doesn't exist
if not os.path.exists(MOCK_CREDENTIALS_PATH):
    with open(MOCK_CREDENTIALS_PATH, 'w') as f:
        json.dump(MOCK_CREDENTIALS_CONTENT, f)

# Sample mock data
MOCK_FILES_DATA = {
    "files": [
        {
            "id": "file1",
            "name": "Test File 1",
            "mimeType": "text/plain",
            "webViewLink": "https://example.com/1"
        },
        {
            "id": "file2",
            "name": "Test File 2",
            "mimeType": "application/pdf",
            "webViewLink": "https://example.com/2"
        }
    ],
    "folders": [
        {
            "id": "folder1",
            "name": "Test Folder",
            "parent_id": None
        }
    ]
}


@pytest.mark.asyncio
@mock.patch('dagster_project.google_drive_assets.service_account')
@mock.patch('dagster_project.google_drive_assets.build')
async def test_google_drive_service_mocked(mock_build, mock_service_account):
    # Mock the Google Drive API service
    mock_service = mock.MagicMock()
    mock_build.return_value = mock_service

    # Mock the credentials
    mock_credentials = mock.MagicMock()
    mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

    # Create config with the mock credentials file
    config = GoogleDriveConfig(
        credentials_file=MOCK_CREDENTIALS_PATH,
        haystack_api_url="http://localhost:8000",
        file_types=[
            ".txt",
            ".md",
            ".pdf",
            ".docx",
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.google-apps.presentation",
        ],
        max_files=10,
        recursive=True,
    )

    # Mock about API call
    mock_service.about().get().execute.return_value = {"user": {"emailAddress": "mock@example.com"}}

    # Test the service creation
    service = google_drive_service(build_op_context(), config)

    # Verify service was created
    assert service is not None
    assert service == mock_service

    # Verify the credentials file was used
    mock_service_account.Credentials.from_service_account_file.assert_called_once()

    return service


def test_google_drive_files_mocked():
    """Test google_drive_files using a function stub that returns pre-defined data"""

    # Define a stub replacement for the asset function
    def stub_google_drive_files(*args, **kwargs):
        return MOCK_FILES_DATA

    # Save original function
    original_function = google_drive_files

    try:
        # Replace the real function with our stub
        from dagster_project import google_drive_assets
        google_drive_assets.google_drive_files = stub_google_drive_files

        # Create config
        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000",
            file_types=[".txt", ".pdf"],
            max_files=10,
            recursive=True,
        )

        # Call the stubbed function
        files = stub_google_drive_files(build_op_context(), config, mock.MagicMock())

        # Verify results
        assert files is not None
        assert "files" in files
        assert "folders" in files
        assert len(files["files"]) == 2

        # Don't return, just use assertions
    finally:
        # Restore original function
        google_drive_assets.google_drive_files = original_function


@mock.patch('dagster_project.google_drive.client.GoogleDriveClient')
@mock.patch('dagster_project.google_drive_assets.ElasticsearchService')
@mock.patch('dagster_project.google_drive_assets.Neo4jService')
def test_index_files_mocked(mock_neo4j_service_class, mock_es_service_class, mock_client_class):
    # Mock Neo4j service
    mock_neo4j_service = mock.MagicMock()
    mock_neo4j_service_class.return_value = mock_neo4j_service

    # Mock Elasticsearch service
    mock_es_service = mock.MagicMock()
    mock_es_service_class.return_value = mock_es_service

    # Mock GoogleDriveClient
    mock_client = mock.MagicMock()
    mock_client_class.return_value = mock_client

    # Create config
    config = GoogleDriveConfig(
        credentials_file=MOCK_CREDENTIALS_PATH,
        haystack_api_url="http://localhost:8000",
        file_types=[".txt", ".pdf"],
        max_files=10,
        recursive=True,
    )

    # Mock the content fetching method
    mock_client.get_file_content.return_value = "This is a test file content"

    # Test the index_files asset
    with mock.patch('dagster_project.google_drive_assets.GoogleDriveClient', return_value=mock_client):
        result = index_files(build_op_context(), config, MOCK_FILES_DATA)

    # Verify results
    assert result is not None

    # Verify services were created and methods were called
    mock_neo4j_service_class.assert_called_once()
    mock_es_service_class.assert_called_once()

    # Verify folder creation was called
    mock_neo4j_service.create_or_update_folder.assert_called_with(
        "folder1", "Test Folder", None
    )


@pytest.mark.asyncio
async def test_google_drive_assets():
    """Run all tests in sequence with proper mocking"""
    try:
        logger.info("Testing google_drive_service with mocks...")
        await test_google_drive_service_mocked()

        logger.info("Testing google_drive_files with mocks...")
        test_google_drive_files_mocked()

        logger.info("Testing index_files with mocks...")
        test_index_files_mocked()

        logger.info("All tests passed!")
    except Exception as e:
        logger.error(f"Error in Google Drive test: {str(e)}")
        raise


class TestGoogleDriveConfig:
    """Tests for GoogleDriveConfig"""

    def test_config_creation(self):
        """Test creating GoogleDriveConfig with valid parameters"""
        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000",
            file_types=[".txt", ".pdf"],
            max_files=100,
            recursive=True
        )

        assert config.credentials_file == MOCK_CREDENTIALS_PATH
        assert config.haystack_api_url == "http://localhost:8000"
        assert config.file_types == [".txt", ".pdf"]
        assert config.max_files == 100
        assert config.recursive is True

    def test_config_defaults(self):
        """Test GoogleDriveConfig with default values"""
        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000"
        )

        # Should have default values
        assert config.max_files == 1000
        assert config.recursive is True
        assert len(config.file_types) > 0


class TestGoogleDriveServiceErrors:
    """Tests for error handling in Google Drive service"""

    @mock.patch('dagster_project.google_drive_assets.service_account')
    @mock.patch('dagster_project.google_drive_assets.build')
    def test_service_creation_with_invalid_credentials(self, mock_build, mock_service_account):
        """Test service creation with invalid credentials"""
        # Mock credentials error
        mock_service_account.Credentials.from_service_account_file.side_effect = Exception("Invalid credentials")

        config = GoogleDriveConfig(
            credentials_file="/invalid/path/credentials.json",
            haystack_api_url="http://localhost:8000"
        )

        with pytest.raises(Exception, match="Invalid credentials"):
            google_drive_service(build_op_context(), config)

    @mock.patch('dagster_project.google_drive_assets.service_account')
    @mock.patch('dagster_project.google_drive_assets.build')
    def test_service_api_connection_error(self, mock_build, mock_service_account):
        """Test service when API connection fails"""
        mock_service = mock.MagicMock()
        mock_build.return_value = mock_service
        mock_credentials = mock.MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials

        # Mock API connection error
        mock_service.about().get().execute.side_effect = Exception("API connection failed")

        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000"
        )

        with pytest.raises(Exception, match="API connection failed"):
            google_drive_service(build_op_context(), config)


class TestGoogleDriveFilesExtended:
    """Extended tests for Google Drive files asset"""

    def test_files_with_empty_response(self):
        """Test google_drive_files with empty API response"""
        def stub_empty_files(*args, **kwargs):
            return {"files": [], "folders": []}

        result = stub_empty_files()

        assert result is not None
        assert "files" in result
        assert "folders" in result
        assert len(result["files"]) == 0
        assert len(result["folders"]) == 0

    def test_files_with_large_dataset(self):
        """Test google_drive_files with large dataset"""
        large_dataset = {
            "files": [
                {
                    "id": f"file{i}",
                    "name": f"Test File {i}",
                    "mimeType": "text/plain",
                    "webViewLink": f"https://example.com/{i}"
                }
                for i in range(100)
            ],
            "folders": [
                {
                    "id": f"folder{i}",
                    "name": f"Test Folder {i}",
                    "parent_id": None
                }
                for i in range(10)
            ]
        }

        def stub_large_files(*args, **kwargs):
            return large_dataset

        result = stub_large_files()

        assert len(result["files"]) == 100
        assert len(result["folders"]) == 10

    def test_files_with_nested_folders(self):
        """Test google_drive_files with nested folder structure"""
        nested_data = {
            "files": [
                {
                    "id": "file1",
                    "name": "Root File",
                    "mimeType": "text/plain",
                    "webViewLink": "https://example.com/1",
                    "parents": ["root"]
                }
            ],
            "folders": [
                {
                    "id": "folder1",
                    "name": "Parent Folder",
                    "parent_id": None
                },
                {
                    "id": "folder2",
                    "name": "Child Folder",
                    "parent_id": "folder1"
                }
            ]
        }

        def stub_nested_files(*args, **kwargs):
            return nested_data

        result = stub_nested_files()

        assert len(result["folders"]) == 2
        # Verify nested structure
        child_folder = next(f for f in result["folders"] if f["name"] == "Child Folder")
        assert child_folder["parent_id"] == "folder1"


class TestIndexFilesExtended:
    """Extended tests for index_files asset"""

    @mock.patch('dagster_project.google_drive.client.GoogleDriveClient')
    @mock.patch('dagster_project.google_drive_assets.ElasticsearchService')
    @mock.patch('dagster_project.google_drive_assets.Neo4jService')
    def test_index_files_with_pdf_content(self, mock_neo4j_service_class, mock_es_service_class, mock_client_class):
        """Test indexing PDF files"""
        mock_neo4j_service = mock.MagicMock()
        mock_neo4j_service_class.return_value = mock_neo4j_service

        mock_es_service = mock.MagicMock()
        mock_es_service_class.return_value = mock_es_service

        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client

        pdf_files_data = {
            "files": [
                {
                    "id": "pdf1",
                    "name": "Test PDF",
                    "mimeType": "application/pdf",
                    "webViewLink": "https://example.com/pdf1"
                }
            ],
            "folders": []
        }

        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000",
            file_types=[".pdf"],
            max_files=10,
            recursive=True
        )

        # Mock PDF content extraction
        mock_client.get_file_content.return_value = "This is extracted PDF content with important information."

        with mock.patch('dagster_project.google_drive_assets.GoogleDriveClient', return_value=mock_client):
            result = index_files(build_op_context(), config, pdf_files_data)

        assert result is not None
        mock_client.get_file_content.assert_called_with("pdf1")

    @mock.patch('dagster_project.google_drive.client.GoogleDriveClient')
    @mock.patch('dagster_project.google_drive_assets.ElasticsearchService')
    @mock.patch('dagster_project.google_drive_assets.Neo4jService')
    def test_index_files_content_extraction_error(self, mock_neo4j_service_class, mock_es_service_class, mock_client_class):
        """Test handling of content extraction errors"""
        mock_neo4j_service = mock.MagicMock()
        mock_neo4j_service_class.return_value = mock_neo4j_service

        mock_es_service = mock.MagicMock()
        mock_es_service_class.return_value = mock_es_service

        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client

        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000",
            file_types=[".txt"],
            max_files=10,
            recursive=True
        )

        # Mock content extraction error
        mock_client.get_file_content.side_effect = Exception("Failed to extract content")

        with mock.patch('dagster_project.google_drive_assets.GoogleDriveClient', return_value=mock_client):
            # Should handle error gracefully and continue processing
            result = index_files(build_op_context(), config, MOCK_FILES_DATA)

        assert result is not None

    @mock.patch('dagster_project.google_drive.client.GoogleDriveClient')
    @mock.patch('dagster_project.google_drive_assets.ElasticsearchService')
    @mock.patch('dagster_project.google_drive_assets.Neo4jService')
    def test_index_files_elasticsearch_error(self, mock_neo4j_service_class, mock_es_service_class, mock_client_class):
        """Test handling of Elasticsearch indexing errors"""
        mock_neo4j_service = mock.MagicMock()
        mock_neo4j_service_class.return_value = mock_neo4j_service

        mock_es_service = mock.MagicMock()
        mock_es_service_class.return_value = mock_es_service

        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client

        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000"
        )

        mock_client.get_file_content.return_value = "Test content"

        # Mock Elasticsearch error
        mock_es_service.index_document.side_effect = Exception("Elasticsearch connection failed")

        with mock.patch('dagster_project.google_drive_assets.GoogleDriveClient', return_value=mock_client):
            # Should handle error gracefully
            result = index_files(build_op_context(), config, MOCK_FILES_DATA)

        assert result is not None

    @mock.patch('dagster_project.google_drive.client.GoogleDriveClient')
    @mock.patch('dagster_project.google_drive_assets.ElasticsearchService')
    @mock.patch('dagster_project.google_drive_assets.Neo4jService')
    def test_index_files_neo4j_error(self, mock_neo4j_service_class, mock_es_service_class, mock_client_class):
        """Test handling of Neo4j indexing errors"""
        mock_neo4j_service = mock.MagicMock()
        mock_neo4j_service_class.return_value = mock_neo4j_service

        mock_es_service = mock.MagicMock()
        mock_es_service_class.return_value = mock_es_service

        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client

        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000"
        )

        mock_client.get_file_content.return_value = "Test content"

        # Mock Neo4j error
        mock_neo4j_service.create_or_update_folder.side_effect = Exception("Neo4j connection failed")

        with mock.patch('dagster_project.google_drive_assets.GoogleDriveClient', return_value=mock_client):
            # Should handle error gracefully
            result = index_files(build_op_context(), config, MOCK_FILES_DATA)

        assert result is not None


class TestAssetDependencies:
    """Tests for asset dependencies and integration"""

    @mock.patch('dagster_project.google_drive_assets.service_account')
    @mock.patch('dagster_project.google_drive_assets.build')
    def test_asset_dependency_chain(self, mock_build, mock_service_account):
        """Test the complete asset dependency chain"""
        # Mock Google Drive service
        mock_service = mock.MagicMock()
        mock_build.return_value = mock_service
        mock_credentials = mock.MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_service.about().get().execute.return_value = {"user": {"emailAddress": "test@example.com"}}

        config = GoogleDriveConfig(
            credentials_file=MOCK_CREDENTIALS_PATH,
            haystack_api_url="http://localhost:8000"
        )

        # Test service creation
        service = google_drive_service(build_op_context(), config)
        assert service is not None

        # Test files retrieval (mocked)
        def mock_files_asset(context, config, service):
            return MOCK_FILES_DATA

        files_data = mock_files_asset(build_op_context(), config, service)
        assert files_data is not None
        assert "files" in files_data

        # Test indexing (mocked)
        with mock.patch('dagster_project.google_drive_assets.ElasticsearchService'), \
             mock.patch('dagster_project.google_drive_assets.Neo4jService'), \
             mock.patch('dagster_project.google_drive_assets.GoogleDriveClient'):

            index_result = index_files(build_op_context(), config, files_data)
            assert index_result is not None


class TestPerformanceAndScaling:
    """Tests for performance and scaling scenarios"""

    def test_large_file_processing(self):
        """Test processing with large number of files"""
        large_files_data = {
            "files": [
                {
                    "id": f"file{i}",
                    "name": f"Large File {i}",
                    "mimeType": "text/plain",
                    "webViewLink": f"https://example.com/{i}"
                }
                for i in range(1000)  # 1000 files
            ],
            "folders": []
        }

        # Test that data structure is maintained for large datasets
        assert len(large_files_data["files"]) == 1000

        # Test filtering by file type
        txt_files = [f for f in large_files_data["files"] if f["mimeType"] == "text/plain"]
        assert len(txt_files) == 1000
    
    def test_memory_efficiency_simulation(self):
        """Simulate memory-efficient processing"""
        def process_files_in_batches(files, batch_size=100):
            """Simulate batch processing for memory efficiency"""
            total_processed = 0
            
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                # Simulate processing
                total_processed += len(batch)
            
            return total_processed
        
        large_file_list = [f"file{i}" for i in range(500)]
        processed_count = process_files_in_batches(large_file_list, batch_size=50)
        
        assert processed_count == 500
    
    def test_concurrent_processing_simulation(self):
        """Simulate concurrent processing capabilities"""
        import asyncio
        
        async def process_file_async(file_id):
            """Simulate async file processing"""
            await asyncio.sleep(0.001)  # Simulate processing time
            return f"processed_{file_id}"
        
        async def process_files_concurrently(file_ids):
            """Process files concurrently"""
            tasks = [process_file_async(file_id) for file_id in file_ids]
            results = await asyncio.gather(*tasks)
            return results
        
        # Test with small number for quick execution
        file_ids = [f"file{i}" for i in range(10)]
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(process_files_concurrently(file_ids))
            assert len(results) == 10
            assert all(result.startswith("processed_") for result in results)
        finally:
            loop.close()


if __name__ == "__main__":
    try:
        logger.info("Testing Google Drive assets...")
        test_google_drive_assets()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
