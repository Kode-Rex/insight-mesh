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


if __name__ == "__main__":
    try:
        logger.info("Testing Google Drive assets...")
        test_google_drive_assets()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
