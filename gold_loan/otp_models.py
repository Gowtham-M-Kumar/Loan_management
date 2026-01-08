from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string


class OTPRecord(models.Model):
    """
    Store OTP records for verification.
    Each OTP is valid for a limited time and can only be used once.
    """
    
    OTP_PURPOSE_LOAN_CREATION = 'loan_creation'
    OTP_PURPOSE_LOAN_CLOSURE = 'loan_closure'
    OTP_PURPOSE_LOAN_EXTENSION = 'loan_extension'
    
    PURPOSE_CHOICES = [
        (OTP_PURPOSE_LOAN_CREATION, 'Loan Creation'),
        (OTP_PURPOSE_LOAN_CLOSURE, 'Loan Closure'),
        (OTP_PURPOSE_LOAN_EXTENSION, 'Loan Extension'),
    ]
    
    # Who is this OTP for
    mobile_number = models.CharField(max_length=10)
    email = models.EmailField(blank=True, null=True)
    
    # OTP Details
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    
    # Reference to what this OTP is for (optional)
    reference_id = models.CharField(max_length=50, blank=True, null=True)  # e.g., loan_id, customer_id
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Attempt tracking
    verification_attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    # Delivery tracking
    sent_via_sms = models.BooleanField(default=False)
    sent_via_email = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mobile_number', 'purpose', 'is_verified']),
            models.Index(fields=['otp_code', 'is_verified']),
        ]
    
    def __str__(self):
        return f"OTP for {self.mobile_number} - {self.purpose} - {'Verified' if self.is_verified else 'Pending'}"
    
    @staticmethod
    def generate_otp_code(length=6):
        """Generate a random numeric OTP code"""
        return ''.join(random.choices(string.digits, k=length))
    
    def is_valid(self):
        """Check if OTP is still valid"""
        if self.is_verified:
            return False
        if self.is_expired:
            return False
        if timezone.now() > self.expires_at:
            self.is_expired = True
            self.save()
            return False
        if self.verification_attempts >= self.max_attempts:
            self.is_expired = True
            self.save()
            return False
        return True
    
    def verify(self, code):
        """
        Verify the OTP code.
        Returns (success: bool, message: str)
        """
        self.verification_attempts += 1
        self.save()
        
        if not self.is_valid():
            return False, "OTP has expired or exceeded maximum attempts"
        
        if self.otp_code != code:
            remaining = self.max_attempts - self.verification_attempts
            if remaining > 0:
                return False, f"Invalid OTP. {remaining} attempt(s) remaining"
            else:
                self.is_expired = True
                self.save()
                return False, "Invalid OTP. Maximum attempts exceeded"
        
        # Success
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
        return True, "OTP verified successfully"
    
    @classmethod
    def create_otp(cls, mobile_number, purpose, reference_id=None, email=None, validity_minutes=10):
        """
        Create a new OTP record.
        Invalidates any previous unverified OTPs for the same mobile/purpose.
        """
        # Invalidate previous OTPs
        cls.objects.filter(
            mobile_number=mobile_number,
            purpose=purpose,
            is_verified=False
        ).update(is_expired=True)
        
        # Generate new OTP - Set to None as Twilio Verify handles the code
        otp_code = None 
        expires_at = timezone.now() + timedelta(minutes=validity_minutes)
        
        otp_record = cls.objects.create(
            mobile_number=mobile_number,
            email=email,
            otp_code=otp_code,
            purpose=purpose,
            reference_id=reference_id,
            expires_at=expires_at
        )
        
        return otp_record
    
    @classmethod
    def get_latest_valid_otp(cls, mobile_number, purpose):
        """Get the latest valid OTP for a mobile number and purpose"""
        try:
            otp = cls.objects.filter(
                mobile_number=mobile_number,
                purpose=purpose,
                is_verified=False,
                is_expired=False
            ).latest('created_at')
            
            if otp.is_valid():
                return otp
            return None
        except cls.DoesNotExist:
            return None
