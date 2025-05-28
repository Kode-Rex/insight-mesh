import sys
import os
import pytest
import tempfile
from unittest.mock import patch

# Add the parent directory to sys.path to allow importing the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from slack_bot.config.settings import SlackSettings, LLMSettings, Settings


class TestConfig:
    """Tests for the configuration system"""

    def test_slack_settings(self):
        """Test SlackSettings configuration"""
        # Test with environment variables
        with patch.dict(os.environ, {
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_APP_TOKEN": "xapp-test-token",
            "SLACK_BOT_ID": "B12345678"
        }):
            settings = SlackSettings()
            assert settings.bot_token.get_secret_value() == "xoxb-test-token"
            assert settings.app_token.get_secret_value() == "xapp-test-token"
            assert settings.bot_id == "B12345678"

    def test_llm_settings(self):
        """Test LLMSettings configuration"""
        # Test with environment variables
        with patch.dict(os.environ, {
            "LLM_API_URL": "http://test-api.com",
            "LLM_API_KEY": "test-api-key",
            "LLM_MODEL": "test-model"
        }):
            settings = LLMSettings()
            assert settings.api_url == "http://test-api.com"
            assert settings.api_key.get_secret_value() == "test-api-key"
            assert settings.model == "test-model"

    def test_settings_defaults(self):
        """Test Settings default values"""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w+') as f:
            f.write("""
            SLACK_BOT_TOKEN=xoxb-temp-token
            SLACK_APP_TOKEN=xapp-temp-token
            LLM_API_URL=http://temp-api.com
            LLM_API_KEY=temp-api-key
            """)
            f.flush()
            
            # Test with env file
            with patch.dict(os.environ, {"ENV_FILE": f.name}):
                with patch('slack_bot.config.settings.SlackSettings') as mock_slack:
                    with patch('slack_bot.config.settings.LLMSettings') as mock_llm:
                        mock_slack.return_value = "slack_settings"
                        mock_llm.return_value = "llm_settings"
                        
                        settings = Settings()
                        assert settings.slack == "slack_settings"
                        assert settings.llm == "llm_settings"
                        assert settings.debug is False
                        assert settings.log_level == "INFO" 