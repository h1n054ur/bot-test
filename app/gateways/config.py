import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

@dataclass
class TwilioConfig:
    """Configuration for Twilio API access."""
    account_sid: str
    auth_token: str
    subaccount_sid: Optional[str] = None
    
    @property
    def active_sid(self) -> str:
        """Return the active account SID (subaccount if set, otherwise main account)."""
        return self.subaccount_sid if self.subaccount_sid else self.account_sid

@dataclass
class AppConfig:
    """Application-wide configuration."""
    twilio: TwilioConfig
    log_to_file: bool = False
    log_path: Optional[str] = None
    debug_mode: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "twilio": {
                "account_sid": self.twilio.account_sid,
                "auth_token": "***REDACTED***",  # Don't serialize the actual token
                "subaccount_sid": self.twilio.subaccount_sid
            },
            "log_to_file": self.log_to_file,
            "log_path": self.log_path,
            "debug_mode": self.debug_mode
        }

def load_config() -> AppConfig:
    """Load configuration from environment variables or .env file.
    
    Returns:
        AppConfig object with loaded configuration
    """
    # Try to load from .env file if it exists
    env_path = Path('.env')
    if env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
        except Exception as e:
            print(f"Warning: Error loading .env file: {e}")
    
    # Get required Twilio credentials
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    
    if not account_sid or not auth_token:
        raise ValueError(
            "Twilio credentials not found. Please set TWILIO_ACCOUNT_SID and "
            "TWILIO_AUTH_TOKEN environment variables or add them to a .env file."
        )
    
    # Get optional configuration
    subaccount_sid = os.environ.get('TWILIO_SUBACCOUNT_SID')
    log_to_file = os.environ.get('LOG_TO_FILE', 'false').lower() == 'true'
    log_path = os.environ.get('LOG_PATH')
    debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
    
    # Create and return config object
    twilio_config = TwilioConfig(
        account_sid=account_sid,
        auth_token=auth_token,
        subaccount_sid=subaccount_sid
    )
    
    return AppConfig(
        twilio=twilio_config,
        log_to_file=log_to_file,
        log_path=log_path,
        debug_mode=debug_mode
    )

# Global config instance
config = load_config()

def save_config_to_file(config: AppConfig, path: str = 'config.json') -> None:
    """Save the current configuration to a JSON file.
    
    Args:
        config: The configuration to save
        path: Path to save the configuration file
    """
    try:
        with open(path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        print(f"Configuration saved to {path}")
    except Exception as e:
        print(f"Error saving configuration: {e}")

def switch_subaccount(subaccount_sid: Optional[str] = None) -> None:
    """Switch to a different subaccount or back to the main account.
    
    Args:
        subaccount_sid: The subaccount SID to switch to, or None to use the main account
    """
    global config
    config.twilio.subaccount_sid = subaccount_sid