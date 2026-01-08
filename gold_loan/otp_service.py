import os
import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

class OTPService:
    """
    Service class to handle OTP generation and delivery via Twilio Verify.
    """

    @staticmethod
    def get_twilio_client():
        """
        Initialize and return Twilio Client.
        """
        account_sid = os.getenv('TWILIO_ACCOUNT_SID') or getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = os.getenv('TWILIO_AUTH_TOKEN') or getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        
        if not account_sid or not auth_token:
            logger.error("Twilio Credentials missing.")
            return None
            
        return Client(account_sid, auth_token)

    @staticmethod
    def normalize_mobile_number(mobile):
        """
        Normalize mobile number to +91XXXXXXXXXX format.
        - Accepts 10 digits, +91, with spaces/hyphens.
        - Returns string formatted as '+91XXXXXXXXXX'.
        - Returns None if invalid.
        """
        if not mobile:
            return None
            
        # Remove non-numeric characters
        cleaned = ''.join(filter(str.isdigit, str(mobile)))
        
        # Handle prefixes
        if cleaned.startswith('91') and len(cleaned) == 12:
            cleaned = cleaned[2:]
        elif cleaned.startswith('0') and len(cleaned) == 11:
            cleaned = cleaned[1:]
            
        # Check length
        if len(cleaned) != 10:
            logger.warning(f"Invalid mobile number length: {mobile}")
            return None
            
        # Return in E.164 format for India (+91)
        return f"+91{cleaned}"

    @staticmethod
    def send_otp_to_customer(mobile_number_ignored=None):
        """
        Send OTP to ADMIN via Twilio Verify.
        Arguments are ignored to enforce sending to Admin only.
        
        Returns:
            tuple: (success (bool), message (str))
        """
        admin_mobile = getattr(settings, 'OTP_ADMIN_MOBILE', None)
        if not admin_mobile:
             logger.error("OTP_ADMIN_MOBILE not set in settings")
             return False, "Admin mobile number not configured"
             
        normalized_number = OTPService.normalize_mobile_number(admin_mobile)
        if not normalized_number:
            return False, "Invalid mobile number"



        # PRODUCTION MODE: Twilio Verify Use
        verify_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID') or getattr(settings, 'TWILIO_VERIFY_SERVICE_SID', None)
        if not verify_sid:
            logger.error("TWILIO_VERIFY_SERVICE_SID is not set.")
            return False, "SMS Configuration Error"

        client = OTPService.get_twilio_client()
        if not client:
             return False, "SMS Service Unavailable"

        try:
            verification = client.verify.v2.services(verify_sid).verifications.create(
                to=normalized_number, 
                channel='sms'
            )
            logger.info(f"Twilio Verify sent to {normalized_number}: {verification.status} (SID: {verification.sid})")
            return True, "OTP sent successfully"
        except TwilioRestException as e:
            logger.error(f"Twilio Error sending OTP to {normalized_number}: {e}")
            return False, f"Twilio Error: {e.msg}"
        except Exception as e:
            logger.error(f"Unexpected error sending OTP: {e}")
            return False, "Failed to send OTP"

    @staticmethod
    def verify_customer_otp(mobile_number_ignored, otp_code):
        """
        Verify OTP using Twilio Verify against ADMIN number.
        
        Args:
            mobile_number_ignored: Ignored, we always verify against admin.
            otp_code (str): The code entered by user.
            
        Returns:
            tuple: (success (bool), message (str))
        """
        admin_mobile = getattr(settings, 'OTP_ADMIN_MOBILE', None)
        if not admin_mobile:
             return False, "Admin mobile number not configured"

        normalized_number = OTPService.normalize_mobile_number(admin_mobile)
        if not normalized_number:
            return False, "Invalid mobile number"

        if not otp_code:
            return False, "OTP code is required"





        # Verify via Twilio
        verify_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID') or getattr(settings, 'TWILIO_VERIFY_SERVICE_SID', None)
        if not verify_sid:
             return False, "Verification Service Error"

        client = OTPService.get_twilio_client()
        if not client:
             return False, "Service Unavailable"

        try:
            verification_check = client.verify.v2.services(verify_sid).verification_checks.create(
                to=normalized_number,
                code=otp_code
            )
            
            if verification_check.status == 'approved':
                logger.info(f"Twilio Verify Success for {normalized_number}")
                return True, "OTP Verified Successfully"
            else:
                logger.warning(f"Twilio Verify Failed for {normalized_number}: {verification_check.status}")
                return False, "Invalid OTP"
                
        except TwilioRestException as e:
            logger.error(f"Twilio Verify Error for {normalized_number}: {e}")
            if e.code == 20404: # Resource not found (expired/invalid)
                 return False, "OTP Expired or Invalid"
            return False, "Incorrect OTP or Expired"
        except Exception as e:
            logger.error(f"Unexpected error verifying OTP: {e}")
            return False, "Verification failed due to system error"
