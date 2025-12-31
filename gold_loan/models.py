from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


# =========================
# VALIDATORS
# =========================

mobile_validator = RegexValidator(
    regex=r'^\d{10}$',
    message="Mobile number must be exactly 10 digits."
)

aadhaar_validator = RegexValidator(
    regex=r'^\d{12}$',
    message="Aadhaar number must be exactly 12 digits."
)


# =========================
# CUSTOMER
# =========================
class Customer(models.Model):
    name = models.CharField(max_length=100)

    mobile_primary = models.CharField(
        max_length=10,
        unique=True,
        validators=[mobile_validator]
    )

    mobile_secondary = models.CharField(
        max_length=10,
        blank=True,
        validators=[mobile_validator]
    )

    email = models.EmailField(blank=True)
    address = models.TextField()

    aadhaar_number = models.CharField(
        max_length=12,
        unique=True,
        validators=[aadhaar_validator]
    )

    profession = models.CharField(max_length=100)

    nominee_name = models.CharField(max_length=100)

    nominee_mobile = models.CharField(
        max_length=10,
        validators=[mobile_validator]
    )

    photo = models.ImageField(upload_to="customers/photos/", blank=True)

    customer_id = models.CharField(max_length=10, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.customer_id or 'No ID'})"

    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = self.generate_customer_id()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_customer_id():
        """Generate unique customer ID in format: PGXXXXXX"""
        # Get the last created customer's ID to increment
        last_customer = Customer.objects.order_by('-id').first()
        
        if last_customer and last_customer.customer_id and last_customer.customer_id.startswith('PG'):
             try:
                 last_seq = int(last_customer.customer_id[2:])
                 new_seq = last_seq + 1
             except ValueError:
                 new_seq = 1
        else:
             # Fallback if no valid previous ID found, or we rely on DB ID count (approx approximation for first run)
             # But better to just check if any exists. 
             # If we are filling existing, 'last_customer' might just be the one with highest ID in DB.
             # If we use ID count, it might clash if rows deleted.
             # Let's count *ids* to be safe or search for max code.
             
             # Robust way: Search for highest PGxxxxx
             last_pg = Customer.objects.filter(customer_id__startswith='PG').order_by('-customer_id').first()
             if last_pg:
                 try:
                     last_seq = int(last_pg.customer_id[2:])
                     new_seq = last_seq + 1
                 except ValueError:
                     new_seq = 1
             else:
                 new_seq = 1

        return f"PG{new_seq:06d}"


# =========================
# LOAN
# =========================
class Loan(models.Model):

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
    ]

    lot_number = models.CharField(max_length=20)
    loan_number = models.CharField(max_length=20, unique=True)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="loans"
    )

    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    price_per_gram = models.DecimalField(max_digits=8, decimal_places=2)

    approved_grams = models.DecimalField(max_digits=6, decimal_places=3)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    pending_interest = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Interest logic dates
    loan_start_date = models.DateTimeField(null=True, blank=True)
    interest_lock_until = models.DateTimeField(null=True, blank=True)
    last_interest_calculated_at = models.DateTimeField(null=True, blank=True)
    last_capitalization_date = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    parent_loan = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='extensions')
    
    # Bank / Pledge Details (added later via edit page)
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    bank_address = models.TextField(blank=True, null=True)
    pledge_receipt_no = models.CharField(max_length=100, blank=True, null=True)
    pledge_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.loan_number

    @staticmethod
    def generate_lot_number():
        """Generate unique lot number in format: LOT-YYYYMMDD-XXXX"""
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Find the last lot number for today
        prefix = f"LOT-{date_str}-"
        last_lot = Loan.objects.filter(lot_number__startswith=prefix).order_by('-lot_number').first()
        
        if last_lot:
            # Extract the sequence number and increment
            last_seq = int(last_lot.lot_number.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        
        return f"{prefix}{new_seq:04d}"

    @staticmethod
    def generate_loan_number():
        """Generate unique loan number in format: LN-YYYYMMDD-XXXX"""
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Find the last loan number for today
        prefix = f"LN-{date_str}-"
        last_loan = Loan.objects.filter(loan_number__startswith=prefix).order_by('-loan_number').first()
        
        if last_loan:
            # Extract the sequence number and increment
            last_seq = int(last_loan.loan_number.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        
        return f"{prefix}{new_seq:04d}"


# =========================
# GOLD ITEM
# =========================
class GoldItem(models.Model):

    CARAT_CHOICES = [
        (18, "18K"),
        (20, "20K"),
        (22, "22K"),
        (24, "24K"),
    ]

    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item_name = models.CharField(max_length=100)
    carat = models.IntegerField(choices=CARAT_CHOICES)

    gross_weight = models.DecimalField(max_digits=6, decimal_places=3)
    approved_net_weight = models.DecimalField(max_digits=6, decimal_places=3)

    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item_name} ({self.approved_net_weight}g)"


class GoldItemBundle(models.Model):
    gold_item = models.OneToOneField(
        GoldItem,
        on_delete=models.CASCADE,
        related_name="bundle"
    )
    item_count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.item_count} items for {self.gold_item.item_name}"


# =========================
# GOLD ITEM IMAGE
# =========================
class GoldItemImage(models.Model):
    gold_item = models.ForeignKey(
        GoldItem,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="gold_items/images/")

    def __str__(self):
        return f"Image for {self.gold_item.item_name}"


# =========================
# LOAN DOCUMENT
# =========================
class LoanDocument(models.Model):

    DOCUMENT_AADHAAR = "aadhaar"
    DOCUMENT_PAN = "pan"
    DOCUMENT_PHOTO = "photo"
    DOCUMENT_DL = "driving_license"
    DOCUMENT_VOTER = "voter_id"
    DOCUMENT_PASSPORT = "passport"
    DOCUMENT_CLOSURE = "closure_receipt"
    DOCUMENT_OTHER = "other"

    DOCUMENT_CHOICES = [
        (DOCUMENT_AADHAAR, "Aadhaar"),
        (DOCUMENT_PAN, "PAN"),
        (DOCUMENT_PHOTO, "Photo"),
        (DOCUMENT_DL, "Driving License"),
        (DOCUMENT_VOTER, "Voter ID"),
        (DOCUMENT_PASSPORT, "Passport"),
        (DOCUMENT_CLOSURE, "Closure Receipt"),
        (DOCUMENT_OTHER, "Other"),
    ]

    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_CHOICES
    )

    other_name = models.CharField(
        max_length=100,
        blank=True
    )

    image = models.FileField(upload_to="loan_documents/", blank=True)

    def __str__(self):
        return f"{self.document_type} document for {self.loan.loan_number}"


# =========================
# PAYMENT
# =========================
class Payment(models.Model):

    PAYMENT_MODE_CASH = "cash"
    PAYMENT_MODE_UPI = "upi"
    PAYMENT_MODE_BANK = "bank"

    PAYMENT_MODE_CHOICES = [
        (PAYMENT_MODE_CASH, "Cash"),
        (PAYMENT_MODE_UPI, "UPI"),
        (PAYMENT_MODE_BANK, "Bank Transfer"),
    ]

    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_component = models.DecimalField(max_digits=12, decimal_places=2)
    principal_component = models.DecimalField(max_digits=12, decimal_places=2)

    payment_date = models.DateField(auto_now_add=True)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES)
    
    reference_no = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} for {self.loan.loan_number}"


# =========================
# LOAN EXPENSE (Internal)
# =========================
class LoanExpense(models.Model):
    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name="expenses"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    medium = models.CharField(max_length=50, blank=True, null=True)  # e.g. Cash, Online
    notes = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.medium}: {self.amount}"


# =========================
# LOAN PLEDGE (Company Data)
# =========================
class LoanPledge(models.Model):
    """
    Separate model to track company's own pledge of the gold to a bank.
    Visible only on edit pages, not for customer or general viewing.
    """
    loan = models.OneToOneField(
        Loan,
        on_delete=models.CASCADE,
        related_name="pledge"
    )

    # Bank / Pledge Info
    bank_name = models.CharField(max_length=200)
    bank_address = models.TextField()
    pledge_receipt_no = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)

    # Gold & Rate Info
    total_actual_grams = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    total_approved_grams = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    price_per_gram = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    interest_period = models.CharField(max_length=50, blank=True, null=True) # e.g. Monthly, Yearly

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pledge for {self.loan.loan_number} at {self.bank_name}"

    @property
    def total_adjustment_amount(self):
        """Auto calculated total of all adjustment amounts."""
        return self.adjustments.aggregate(total=models.Sum('amount'))['total'] or 0


class LoanPledgeAdjustment(models.Model):
    """
    Dynamic rows for Profit / Adjustment Tracking within a LoanPledge.
    """
    pledge = models.ForeignKey(
        LoanPledge,
        on_delete=models.CASCADE,
        related_name="adjustments"
    )

    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    medium = models.CharField(max_length=50) # Cash, Online, etc.
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date}: {self.amount} via {self.medium}"


