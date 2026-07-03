from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import LoanApplication,  UserProfile


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_no",           # Invoice No (primary)
        "customer_name",        # Customer Name
        "invoice_amount",       # Invoice Amount
        "received_amount",      # Received Amount
        "balance_amount",       # Balance Amount
        "payment_status",       # Payment Status
        "invoice_due_date",     # Due Date
        "whatsapp",             # WhatsApp Number
        "email",                # Email
    )
    list_filter = ("payment_status", "invoice_due_date", "employee_name")
    search_fields = (
        "invoice_no", 
        "customer_name", 
        "item_name", 
        "employee_name",
        "whatsapp", 
        "email"
    )
    list_per_page = 20
    ordering = ("-invoice_due_date",)
    
    # Fields to show in detail view
    fieldsets = (
        ("Invoice Information", {
            "fields": (
                "invoice_no", 
                "invoice_date", 
                "invoice_due_date",
                "customer_name",
            )
        }),
        ("Item Details", {
            "fields": (
                "item_name",
                "item_sales_qty",
                "item_sales_uom", 
                "item_rate",
                "item_amount",
            )
        }),
        ("Payment Details", {
            "fields": (
                "invoice_amount",
                "received_amount",
                "balance_amount",
                "payment_status",
                "overdue_days",
            )
        }),
        ("Employee & Credit", {
            "fields": (
                "employee_name",
                "credit_term",
            )
        }),
        ("Contact Information", {
            "fields": (
                "whatsapp",
                "email",
            )
        }),
        ("Tracking", {
            "fields": (
                "created_at",
                "updated_at",
                "last_email_sent_at",
                "last_whatsapp_sent_at",
            ),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ("created_at", "updated_at", "last_email_sent_at", "last_whatsapp_sent_at")
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ("invoice_no",)
        return self.readonly_fields


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "created_at", "last_login_time")
    list_filter = ("created_at", "last_login_time")
    search_fields = ("user__username", "user__email", "email")
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("User Information", {
            "fields": (
                "user",
                "email",
            )
        }),
        ("Login Tracking", {
            "fields": (
                "last_login_time",
                "created_at",
                "updated_at",
            )
        }),
    )


# Optional: Customize User admin to show profile inline
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "last_login")
    search_fields = ("username", "email", "first_name", "last_name")


# Unregister default User admin and register custom one
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)




from .models import LoanApplication, UserProfile, BankDetail

@admin.register(BankDetail)
class BankDetailAdmin(admin.ModelAdmin):
    list_display = ('beneficiary_name', 'bank_name', 'email_sender_name', 'account_no', 'ifsc_code', 'is_active')
    list_editable = ('is_active',)
    fieldsets = (
        ('Bank Information', {
            'fields': ('beneficiary_name', 'account_no', 'bank_name', 'branch_name', 'ifsc_code')
        }),
        ('Email & Notifications', {
            'fields': ('email_sender_name',),
            'description': 'Company name to use in email and WhatsApp signatures (e.g., Mahima Life Sciences, Vincit Lab Pvt Ltd)'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )




from django.contrib import admin
from .models import ExcelBatch, LoanApplicationArchive


# ==============================
# LoanApplicationArchive Inline
# ==============================
class LoanApplicationArchiveInline(admin.TabularInline):
    model = LoanApplicationArchive
    extra = 0
    fields = (
        'invoice_no',
        'customer_name',
        'invoice_amount',
        'received_amount',
        'balance_amount',
        'payment_status',
        'archived_at',
    )
    readonly_fields = ('archived_at',)
    show_change_link = True


# ==============================
# ExcelBatch Admin
# ==============================
@admin.register(ExcelBatch)
class ExcelBatchAdmin(admin.ModelAdmin):
    list_display = (
        'batch_id',
        'file_name',
        'file_size',
        'total_records',
        'uploaded_by',
        'uploaded_at',
    )
    
    search_fields = (
        'batch_id',
        'file_name',
        'uploaded_by',
    )
    
    list_filter = (
        'uploaded_at',
        'uploaded_by',
    )
    
    readonly_fields = ('uploaded_at',)
    
    ordering = ('-uploaded_at',)
    
    inlines = [LoanApplicationArchiveInline]


# ==============================
# LoanApplicationArchive Admin
# ==============================
@admin.register(LoanApplicationArchive)
class LoanApplicationArchiveAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_no',
        'customer_name',
        'invoice_amount',
        'received_amount',
        'balance_amount',
        'payment_status',
        'batch_number',
        'archived_at',
    )

    search_fields = (
        'invoice_no',
        'customer_name',
        'email',
        'whatsapp',
    )

    list_filter = (
        'payment_status',
        'batch_number',
        'archived_at',
    )

    readonly_fields = ('archived_at',)

    ordering = ('-archived_at',)

    list_per_page = 50

    # Performance optimization
    list_select_related = ('batch',)

    # Optional bulk actions
    actions = ['mark_as_paid']

    def mark_as_paid(self, request, queryset):
        queryset.update(payment_status='paid')
    mark_as_paid.short_description = "Mark selected as Paid"


from .models import FollowUp

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('application', 'followup_type', 'followup_date', 'status', 'ptp_date', 'ptp_amount', 'created_at')
    list_filter = ('followup_type', 'status', 'followup_date', 'ptp_date')
    search_fields = ('application__customer_name', 'application__invoice_no', 'notes')
    ordering = ('-followup_date', '-created_at')





