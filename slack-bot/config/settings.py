from pydantic import HttpUrl, SecretStr, Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional

class SlackSettings(BaseSettings):
    """Slack API settings"""
    bot_token: SecretStr
    app_token: SecretStr
    bot_id: str = ""
    
    model_config = ConfigDict(env_prefix="SLACK_")

class LLMSettings(BaseSettings):
    """LLM API settings"""
    api_url: str = Field(..., description="LLM API URL")
    api_key: SecretStr
    model: str = "gpt-4o-mini"
    
    model_config = ConfigDict(env_prefix="LLM_")

class AgentSettings(BaseSettings):
    """Agent process settings"""
    enabled: bool = True
    
    model_config = ConfigDict(env_prefix="AGENT_")

class Settings(BaseSettings):
    """Main application settings"""
    slack: SlackSettings = SlackSettings()
    llm: LLMSettings = LLMSettings()
    agent: AgentSettings = AgentSettings()
    debug: bool = False
    log_level: str = "INFO"
    
    model_config = ConfigDict(env_file=".env")

# Create a singleton instance
settings = Settings() 