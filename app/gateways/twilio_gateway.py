import requests
from typing import Dict, List, Any, Optional, Union, Tuple
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.gateways.config import config
from app.gateways.file_logger import file_logger

class TwilioGateway:
    """Gateway for interacting with the Twilio API.
    
    This class wraps the Twilio SDK client and provides methods for common operations.
    """
    
    def __init__(self):
        """Initialize the Twilio gateway with credentials from config."""
        self.account_sid = config.twilio.account_sid
        self.auth_token = config.twilio.auth_token
        self.client = Client(self.account_sid, self.auth_token)
        
        # If a subaccount is configured, use it
        if config.twilio.subaccount_sid:
            self.active_sid = config.twilio.subaccount_sid
        else:
            self.active_sid = self.account_sid
    
    def refresh_client(self) -> None:
        """Refresh the Twilio client with the current configuration.
        
        This should be called after switching subaccounts.
        """
        self.client = Client(self.account_sid, self.auth_token)
        self.active_sid = config.twilio.active_sid
    
    def search_phone_numbers(self, country_code: str, 
                            area_code: Optional[str] = None,
                            contains: Optional[str] = None,
                            sms_enabled: bool = False,
                            voice_enabled: bool = False,
                            limit: int = 20) -> Tuple[List[Dict[str, Any]], bool]:
        """Search for available phone numbers using the Twilio API.
        
        Args:
            country_code: Two-letter country code (e.g., 'US')
            area_code: Optional area code to filter by
            contains: Optional sequence of digits to search for
            sms_enabled: Whether the number should support SMS
            voice_enabled: Whether the number should support voice
            limit: Maximum number of results to return
            
        Returns:
            Tuple of (list of phone number dictionaries, has_more_results flag)
        """
        try:
            # Build filter parameters
            params = {}
            if area_code:
                params['AreaCode'] = area_code
            if contains:
                params['Contains'] = contains
            if sms_enabled:
                params['SmsEnabled'] = 'true'
            if voice_enabled:
                params['VoiceEnabled'] = 'true'
            
            # Make the API request
            numbers = self.client.available_phone_numbers(country_code) \
                          .local.list(limit=limit, **params)
            
            # Convert to dictionaries
            results = []
            for number in numbers:
                results.append({
                    'phone_number': number.phone_number,
                    'friendly_name': number.friendly_name,
                    'locality': number.locality,
                    'region': number.region,
                    'postal_code': number.postal_code,
                    'iso_country': number.iso_country,
                    'capabilities': {
                        'voice': number.capabilities.get('voice', False),
                        'sms': number.capabilities.get('sms', False),
                        'mms': number.capabilities.get('mms', False)
                    }
                })
            
            # Determine if there are more results
            has_more = len(numbers) >= limit
            
            return results, has_more
            
        except TwilioRestException as e:
            file_logger.log_error('twilio_search', f"Error searching for phone numbers: {str(e)}")
            return [], False
    
    def search_phone_numbers_raw(self, country_code: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for available phone numbers using raw HTTP requests.
        
        This method is used for the batch search functionality, which needs to make
        multiple requests quickly.
        
        Args:
            country_code: Two-letter country code (e.g., 'US')
            params: Dictionary of query parameters
            
        Returns:
            Raw API response as a dictionary
        """
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.active_sid}/AvailablePhoneNumbers/{country_code}/Local.json"
        
        response = requests.get(
            url,
            params=params,
            auth=(self.account_sid, self.auth_token)
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"Error {response.status_code}: {response.text}"
            file_logger.log_error('twilio_search_raw', error_msg)
            return {"available_phone_numbers": []}
    
    def purchase_phone_number(self, phone_number: str, 
                             friendly_name: Optional[str] = None) -> Dict[str, Any]:
        """Purchase a phone number from Twilio.
        
        Args:
            phone_number: The phone number to purchase (in E.164 format)
            friendly_name: Optional friendly name for the number
            
        Returns:
            Dictionary with purchase result
        """
        try:
            kwargs = {}
            if friendly_name:
                kwargs['friendly_name'] = friendly_name
                
            incoming_number = self.client.incoming_phone_numbers.create(
                phone_number=phone_number,
                account_sid=self.active_sid,
                **kwargs
            )
            
            result = {
                'success': True,
                'sid': incoming_number.sid,
                'phone_number': incoming_number.phone_number,
                'friendly_name': incoming_number.friendly_name,
                'date_created': str(incoming_number.date_created),
                'capabilities': incoming_number.capabilities
            }
            
            # Log the purchase
            file_logger.log_purchase(
                phone_number=incoming_number.phone_number,
                status='purchased',
                price=None,  # Twilio API doesn't return price in the response
                sid=incoming_number.sid
            )
            
            return result
            
        except TwilioRestException as e:
            error_msg = f"Error purchasing phone number: {str(e)}"
            file_logger.log_purchase(
                phone_number=phone_number,
                status='failed',
                error=error_msg
            )
            return {
                'success': False,
                'error': error_msg,
                'phone_number': phone_number
            }
    
    def get_account_phone_numbers(self) -> List[Dict[str, Any]]:
        """Get all phone numbers associated with the account.
        
        Returns:
            List of phone number dictionaries
        """
        try:
            numbers = self.client.incoming_phone_numbers.list(account_sid=self.active_sid)
            
            results = []
            for number in numbers:
                results.append({
                    'sid': number.sid,
                    'phone_number': number.phone_number,
                    'friendly_name': number.friendly_name,
                    'date_created': str(number.date_created),
                    'capabilities': number.capabilities,
                    'voice_url': number.voice_url,
                    'sms_url': number.sms_url,
                    'voice_method': number.voice_method,
                    'sms_method': number.sms_method,
                    'status_callback': number.status_callback,
                    'status_callback_method': number.status_callback_method
                })
            
            return results
            
        except TwilioRestException as e:
            file_logger.log_error('twilio_get_numbers', f"Error getting phone numbers: {str(e)}")
            return []
    
    def release_phone_number(self, sid: str) -> bool:
        """Release a phone number from the account.
        
        Args:
            sid: The SID of the phone number to release
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the phone number first for logging
            number = self.client.incoming_phone_numbers(sid).fetch()
            phone_number = number.phone_number
            
            # Delete the number
            self.client.incoming_phone_numbers(sid).delete()
            
            # Log the release
            file_logger.log_purchase(
                phone_number=phone_number,
                status='released',
                sid=sid
            )
            
            return True
            
        except TwilioRestException as e:
            error_msg = f"Error releasing phone number: {str(e)}"
            file_logger.log_error('twilio_release', error_msg)
            return False
    
    def update_phone_number(self, sid: str, 
                           friendly_name: Optional[str] = None,
                           sms_url: Optional[str] = None,
                           sms_method: Optional[str] = None,
                           voice_url: Optional[str] = None,
                           voice_method: Optional[str] = None) -> Dict[str, Any]:
        """Update a phone number's configuration.
        
        Args:
            sid: The SID of the phone number to update
            friendly_name: Optional new friendly name
            sms_url: Optional new SMS URL
            sms_method: Optional new SMS method (GET or POST)
            voice_url: Optional new voice URL
            voice_method: Optional new voice method (GET or POST)
            
        Returns:
            Dictionary with update result
        """
        try:
            kwargs = {}
            if friendly_name is not None:
                kwargs['friendly_name'] = friendly_name
            if sms_url is not None:
                kwargs['sms_url'] = sms_url
            if sms_method is not None:
                kwargs['sms_method'] = sms_method
            if voice_url is not None:
                kwargs['voice_url'] = voice_url
            if voice_method is not None:
                kwargs['voice_method'] = voice_method
                
            number = self.client.incoming_phone_numbers(sid).update(**kwargs)
            
            return {
                'success': True,
                'sid': number.sid,
                'phone_number': number.phone_number,
                'friendly_name': number.friendly_name,
                'voice_url': number.voice_url,
                'sms_url': number.sms_url,
                'voice_method': number.voice_method,
                'sms_method': number.sms_method
            }
            
        except TwilioRestException as e:
            error_msg = f"Error updating phone number: {str(e)}"
            file_logger.log_error('twilio_update', error_msg)
            return {
                'success': False,
                'error': error_msg,
                'sid': sid
            }
    
    def make_call(self, from_number: str, to_number: str, 
                 url: Optional[str] = None,
                 twiml: Optional[str] = None) -> Dict[str, Any]:
        """Make an outbound call using Twilio.
        
        Args:
            from_number: The number to call from
            to_number: The number to call
            url: Optional TwiML URL to execute when the call connects
            twiml: Optional TwiML to execute when the call connects
            
        Returns:
            Dictionary with call result
        """
        try:
            kwargs = {
                'to': to_number,
                'from_': from_number
            }
            
            if url:
                kwargs['url'] = url
            elif twiml:
                kwargs['twiml'] = twiml
            
            call = self.client.calls.create(**kwargs)
            
            # Log the call
            file_logger.log_call(
                from_number=from_number,
                to_number=to_number,
                status=call.status,
                sid=call.sid
            )
            
            return {
                'success': True,
                'sid': call.sid,
                'status': call.status,
                'from': from_number,
                'to': to_number,
                'direction': call.direction,
                'date_created': str(call.date_created)
            }
            
        except TwilioRestException as e:
            error_msg = f"Error making call: {str(e)}"
            file_logger.log_call(
                from_number=from_number,
                to_number=to_number,
                status='failed',
                error=error_msg
            )
            return {
                'success': False,
                'error': error_msg,
                'from': from_number,
                'to': to_number
            }
    
    def send_message(self, from_number: str, to_number: str, 
                    body: str) -> Dict[str, Any]:
        """Send an SMS message using Twilio.
        
        Args:
            from_number: The number to send from
            to_number: The number to send to
            body: The message body
            
        Returns:
            Dictionary with message result
        """
        try:
            message = self.client.messages.create(
                to=to_number,
                from_=from_number,
                body=body
            )
            
            # Log the message
            file_logger.log_message(
                from_number=from_number,
                to_number=to_number,
                status=message.status,
                body=body,
                sid=message.sid
            )
            
            return {
                'success': True,
                'sid': message.sid,
                'status': message.status,
                'from': from_number,
                'to': to_number,
                'body': body,
                'date_created': str(message.date_created)
            }
            
        except TwilioRestException as e:
            error_msg = f"Error sending message: {str(e)}"
            file_logger.log_message(
                from_number=from_number,
                to_number=to_number,
                status='failed',
                body=body,
                error=error_msg
            )
            return {
                'success': False,
                'error': error_msg,
                'from': from_number,
                'to': to_number,
                'body': body
            }
    
    def get_call_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent call logs from the account.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of call log dictionaries
        """
        try:
            calls = self.client.calls.list(limit=limit)
            
            results = []
            for call in calls:
                results.append({
                    'sid': call.sid,
                    'from': call.from_,
                    'to': call.to,
                    'status': call.status,
                    'direction': call.direction,
                    'duration': call.duration,
                    'price': call.price,
                    'date_created': str(call.date_created)
                })
            
            return results
            
        except TwilioRestException as e:
            file_logger.log_error('twilio_call_logs', f"Error getting call logs: {str(e)}")
            return []
    
    def get_message_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent message logs from the account.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of message log dictionaries
        """
        try:
            messages = self.client.messages.list(limit=limit)
            
            results = []
            for message in messages:
                results.append({
                    'sid': message.sid,
                    'from': message.from_,
                    'to': message.to,
                    'body': message.body,
                    'status': message.status,
                    'direction': message.direction,
                    'price': message.price,
                    'date_created': str(message.date_created)
                })
            
            return results
            
        except TwilioRestException as e:
            file_logger.log_error('twilio_message_logs', f"Error getting message logs: {str(e)}")
            return []
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get information about the current account.
        
        Returns:
            Dictionary with account information
        """
        try:
            account = self.client.api.accounts(self.active_sid).fetch()
            
            return {
                'sid': account.sid,
                'friendly_name': account.friendly_name,
                'status': account.status,
                'type': account.type,
                'date_created': str(account.date_created),
                'date_updated': str(account.date_updated)
            }
            
        except TwilioRestException as e:
            file_logger.log_error('twilio_account_info', f"Error getting account info: {str(e)}")
            return {
                'error': str(e)
            }
    
    def get_subaccounts(self) -> List[Dict[str, Any]]:
        """Get all subaccounts associated with the main account.
        
        Returns:
            List of subaccount dictionaries
        """
        try:
            # Only fetch subaccounts if we're on the main account
            if self.active_sid == self.account_sid:
                accounts = self.client.api.accounts.list(
                    friendly_name=lambda name: name != "Twilio"  # Filter out the main account
                )
                
                results = []
                for account in accounts:
                    results.append({
                        'sid': account.sid,
                        'friendly_name': account.friendly_name,
                        'status': account.status,
                        'type': account.type,
                        'date_created': str(account.date_created)
                    })
                
                return results
            else:
                return []
                
        except TwilioRestException as e:
            file_logger.log_error('twilio_subaccounts', f"Error getting subaccounts: {str(e)}")
            return []
    
    def create_subaccount(self, friendly_name: str) -> Dict[str, Any]:
        """Create a new subaccount.
        
        Args:
            friendly_name: The friendly name for the new subaccount
            
        Returns:
            Dictionary with subaccount creation result
        """
        try:
            account = self.client.api.accounts.create(friendly_name=friendly_name)
            
            return {
                'success': True,
                'sid': account.sid,
                'friendly_name': account.friendly_name,
                'status': account.status,
                'date_created': str(account.date_created)
            }
            
        except TwilioRestException as e:
            error_msg = f"Error creating subaccount: {str(e)}"
            file_logger.log_error('twilio_create_subaccount', error_msg)
            return {
                'success': False,
                'error': error_msg
            }

# Create a global instance of the Twilio gateway
twilio_gateway = TwilioGateway()