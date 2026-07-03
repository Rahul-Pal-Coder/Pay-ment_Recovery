from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class LoanApplication(models.Model):
    COMPANY_CHOICES = [
        ('Mahima', 'Mahima Life Sciences Pvt Ltd'),
        ('Vincit', 'Vincit Labs Pvt Ltd'),
    ]
    
    company = models.CharField(
        max_length=50,
        choices=COMPANY_CHOICES,
        default='Mahima',
        db_index=True
    )
    # Excel ke 18 columns ke according fields
    invoice_no = models.CharField(max_length=100, unique=True)
    invoice_date = models.DateField()
    customer_name = models.CharField(max_length=255)
    item_name = models.CharField(max_length=255, blank=True, null=True)
    item_sales_qty = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    item_sales_uom = models.CharField(max_length=50, blank=True, null=True)
    item_rate = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    item_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    employee_name = models.CharField(max_length=255, blank=True, null=True)
    credit_term = models.CharField(max_length=100, blank=True, null=True)
    invoice_due_date = models.DateField()
    invoice_amount = models.DecimalField(max_digits=15, decimal_places=2)
    received_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    overdue_days = models.IntegerField(blank=True, null=True)
    payment_status = models.CharField(max_length=50, default='pending')
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_email_sent_at = models.DateTimeField(blank=True, null=True)
    last_whatsapp_sent_at = models.DateTimeField(blank=True, null=True)
    
    # Email threading - stores Message-ID for conversation threading
    email_message_id = models.CharField(max_length=255, blank=True, null=True,
        help_text='Last email Message-ID for threading replies in same conversation')

    # Soft delete fields
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-invoice_due_date']
    
    def __str__(self):
        return f"[{self.company}] {self.customer_name} - {self.invoice_no}"
    
    @property
    def current_overdue_days(self):
        if self.payment_status == 'paid':
            return 0
        
        today = timezone.localdate()
        if self.invoice_due_date and self.invoice_due_date < today:
            return (today - self.invoice_due_date).days
        return 0

    @property
    def is_overdue(self):
        if self.payment_status == 'paid':
            return False
        return self.current_overdue_days > 0
    
    @property
    def status_display(self):
        if self.payment_status == 'paid':
            return "PAID"
        
        days = self.current_overdue_days
        if days > 0:
            return f"OVERDUE ({days} Days)"
        
        return "PENDING"

    @property
    def due_summary(self):
        if self.payment_status == 'paid':
            return "Paid"
        
        today = timezone.localdate()
        days_diff = (self.invoice_due_date - today).days
        
        if days_diff < 0:
            return f"Overdue by {abs(days_diff)} days"
        elif days_diff == 0:
            return "Due Today"
        return f"{days_diff} days left"

    @property
    def recovery_priority(self):
        if self.payment_status == 'paid':
            return 'Paid'
        days = self.current_overdue_days
        if days > 90:
            return 'High Risk'
        elif 30 <= days <= 90:
            return 'Medium Risk'
        return 'Low Risk'

    @property
    def recovery_priority_emoji(self):
        if self.payment_status == 'paid':
            return '🟢'
        days = self.current_overdue_days
        if days > 90:
            return '🔥'
        elif 30 <= days <= 90:
            return '🟡'
        return '🟢'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email = models.EmailField(blank=True, null=True)
    signup_time = models.DateTimeField(auto_now_add=True)
    last_login_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.email or 'No email'}"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class BankDetail(models.Model):
    beneficiary_name = models.CharField(max_length=255, default='Mahima Life Sciences Pvt Ltd')
    account_no = models.CharField(max_length=100, default='MLSP96')
    bank_name = models.CharField(max_length=255, default='HDFC Bank Ltd.')
    branch_name = models.CharField(max_length=255, default='Rohini Sector 9 – Northex Mall – New Delhi, Delhi')
    ifsc_code = models.CharField(max_length=50, default='HDFC0001347')
    email_sender_name = models.CharField(max_length=255, default='Mahima Life Sciences', help_text='Company name for email and WhatsApp signature')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Bank Detail"
        verbose_name_plural = "Bank Details"
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_no}"


class ExcelBatch(models.Model):
    batch_id = models.CharField(max_length=100, unique=True)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="Size in KB")
    total_records = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.CharField(max_length=150, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Excel Batch"
        verbose_name_plural = "Excel Batches"
    
    def __str__(self):
        return f"{self.batch_id} - {self.file_name} ({self.uploaded_at})"


class LoanApplicationArchive(models.Model):
    batch = models.ForeignKey(ExcelBatch, on_delete=models.CASCADE, related_name='records', null=True, blank=True)
    batch_number = models.IntegerField(help_text="Batch sequence number", null=True, blank=True)
    
    company = models.CharField(
        max_length=50,
        choices=[('Mahima', 'Mahima Life Sciences Pvt Ltd'), ('Vincit', 'Vincit Labs Pvt Ltd')],
        default='Mahima',
        db_index=True
    )
    invoice_no = models.CharField(max_length=100)
    invoice_date = models.DateField()
    customer_name = models.CharField(max_length=255)
    item_name = models.CharField(max_length=255, blank=True, null=True)
    item_sales_qty = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    item_sales_uom = models.CharField(max_length=50, blank=True, null=True)
    item_rate = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    item_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    employee_name = models.CharField(max_length=255, blank=True, null=True)
    credit_term = models.CharField(max_length=100, blank=True, null=True)
    invoice_due_date = models.DateField()
    invoice_amount = models.DecimalField(max_digits=15, decimal_places=2)
    received_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    overdue_days = models.IntegerField(blank=True, null=True)
    payment_status = models.CharField(max_length=50, default='pending')
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.CharField(max_length=150, blank=True, null=True)
    
    class Meta:
        ordering = ['-archived_at', 'batch_number']
        indexes = [
            models.Index(fields=['batch', 'batch_number']),
            models.Index(fields=['customer_name']),
            models.Index(fields=['invoice_no']),
        ]
    
    def __str__(self):
        batch_info = f"Batch {self.batch_number}" if self.batch_number else "No Batch"
        return f"[{self.company}] {batch_info}: {self.customer_name} - {self.invoice_no}"


class FollowUp(models.Model):
    FOLLOWUP_TYPES = [
        ('Call', 'Call'),
        ('Email', 'Email'),
        ('WhatsApp', 'WhatsApp'),
        ('PTP', 'Promise to Pay (PTP)'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='followups')
    followup_type = models.CharField(max_length=50, choices=FOLLOWUP_TYPES, default='Call')
    followup_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    
    # Promise to Pay details
    ptp_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ptp_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-followup_date', '-created_at']
        
    def __str__(self):
        return f"{self.followup_type} for {self.application.customer_name} on {self.followup_date}"