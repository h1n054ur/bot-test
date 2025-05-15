import os
import json
import logging
import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from app.gateways.config import config

class FileLogger:
    """File-based logger that writes structured JSON logs.
    
    This logger is optional and only active if log_to_file is enabled in the config.
    """
    
    def __init__(self):
        """Initialize the file logger."""
        self.enabled = config.log_to_file
        self.log_path = config.log_path or 'logs'
        
        if self.enabled:
            # Create log directory if it doesn't exist
            Path(self.log_path).mkdir(parents=True, exist_ok=True)
            
            # Set up Python's logging module for standard logs
            log_file = os.path.join(self.log_path, 'app.log')
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            self.logger = logging.getLogger('twilio_manager')
            self.logger.info("File logger initialized")
    
    def _get_log_file_path(self, log_type: str) -> str:
        """Get the path to a specific log file.
        
        Args:
            log_type: The type of log (e.g., 'call', 'message', 'purchase')
            
        Returns:
            The path to the log file
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.log_path, f"{log_type}_{today}.json")
    
    def _write_json_log(self, log_type: str, data: Dict[str, Any]) -> None:
        """Write a JSON log entry to the appropriate log file.
        
        Args:
            log_type: The type of log
            data: The data to log
        """
        if not self.enabled:
            return
        
        # Add timestamp to the log entry
        data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Get the log file path
        log_file = self._get_log_file_path(log_type)
        
        # Read existing logs if the file exists
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                # If the file is corrupted, start with an empty list
                logs = []
        
        # Append the new log entry
        logs.append(data)
        
        # Write the updated logs back to the file
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def log_call(self, from_number: str, to_number: str, status: str, 
                sid: Optional[str] = None, duration: Optional[int] = None,
                error: Optional[str] = None) -> None:
        """Log a call to the call log file.
        
        Args:
            from_number: The number the call is from
            to_number: The number the call is to
            status: The status of the call
            sid: Optional Twilio call SID
            duration: Optional call duration in seconds
            error: Optional error message if the call failed
        """
        data = {
            'from': from_number,
            'to': to_number,
            'status': status,
            'sid': sid,
            'duration': duration,
            'error': error
        }
        self._write_json_log('call', data)
        
        # Also log to standard logger
        if self.enabled:
            log_msg = f"Call from {from_number} to {to_number}: {status}"
            if error:
                self.logger.error(f"{log_msg} - Error: {error}")
            else:
                self.logger.info(log_msg)
    
    def log_message(self, from_number: str, to_number: str, status: str,
                   body: Optional[str] = None, sid: Optional[str] = None,
                   error: Optional[str] = None) -> None:
        """Log a message to the message log file.
        
        Args:
            from_number: The number the message is from
            to_number: The number the message is to
            status: The status of the message
            body: Optional message body (truncated if too long)
            sid: Optional Twilio message SID
            error: Optional error message if the message failed
        """
        # Truncate message body if it's too long
        if body and len(body) > 100:
            body = body[:97] + '...'
            
        data = {
            'from': from_number,
            'to': to_number,
            'status': status,
            'body': body,
            'sid': sid,
            'error': error
        }
        self._write_json_log('message', data)
        
        # Also log to standard logger
        if self.enabled:
            log_msg = f"Message from {from_number} to {to_number}: {status}"
            if error:
                self.logger.error(f"{log_msg} - Error: {error}")
            else:
                self.logger.info(log_msg)
    
    def log_purchase(self, phone_number: str, status: str, price: Optional[float] = None,
                    sid: Optional[str] = None, error: Optional[str] = None) -> None:
        """Log a phone number purchase to the purchase log file.
        
        Args:
            phone_number: The purchased phone number
            status: The status of the purchase
            price: Optional price of the number
            sid: Optional Twilio phone number SID
            error: Optional error message if the purchase failed
        """
        data = {
            'phone_number': phone_number,
            'status': status,
            'price': price,
            'sid': sid,
            'error': error
        }
        self._write_json_log('purchase', data)
        
        # Also log to standard logger
        if self.enabled:
            log_msg = f"Purchase of {phone_number}: {status}"
            if price is not None:
                log_msg += f" (${price:.2f})"
            if error:
                self.logger.error(f"{log_msg} - Error: {error}")
            else:
                self.logger.info(log_msg)
    
    def log_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log an error to the error log file.
        
        Args:
            error_type: The type of error
            message: The error message
            details: Optional additional details about the error
        """
        data = {
            'type': error_type,
            'message': message,
            'details': details or {}
        }
        self._write_json_log('error', data)
        
        # Also log to standard logger
        if self.enabled:
            self.logger.error(f"{error_type}: {message}")

# Create a global instance of the file logger
file_logger = FileLogger()