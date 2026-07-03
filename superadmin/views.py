from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.db.models.functions import TruncMonth

from notifications.models import LoanApplication, UserProfile, FollowUp


def is_superadmin(user):
    """Check if user is superuser (Super Admin)"""
    return user.is_authenticated and user.is_superuser


def superadmin_login_view(request):
    """Separate login page for Super Admin"""
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('superadmin:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome Super Admin {username}!")
                return redirect('superadmin:dashboard')
            else:
                messages.error(request, "Access denied. Only Super Admin can login here.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'superadmin/login.html')


def superadmin_logout_view(request):
    """Logout Super Admin"""
    logout(request)
    messages.success(request, "Super Admin logged out successfully.")
    return redirect('superadmin:login')


@login_required(login_url='/superadmin/login/')
@user_passes_test(is_superadmin, login_url='/superadmin/login/')
def superadmin_dashboard_view(request):
    """Super Admin Dashboard — shows all employees and their summary stats"""
    today = timezone.localdate()

    # --- All System Stats ---
    all_records = LoanApplication.objects.filter(is_active=True)
    total_stats = all_records.aggregate(
        total_records=Count('id'),
        total_invoice_amount=Sum('invoice_amount'),
        total_received=Sum('received_amount'),
        total_balance=Sum('balance_amount'),
    )

    status_counts = all_records.aggregate(
        paid_count=Count('id', filter=Q(payment_status__iexact='paid')),
        pending_count=Count('id', filter=~Q(payment_status__iexact='paid') & Q(invoice_due_date__gte=today)),
        overdue_count=Count('id', filter=~Q(payment_status__iexact='paid') & Q(invoice_due_date__lt=today)),
    )

    # Risk categories
    high_risk = all_records.filter(
        ~Q(payment_status__iexact='paid'),
        invoice_due_date__lt=today - timezone.timedelta(days=90)
    ).count()
    medium_risk = all_records.filter(
        ~Q(payment_status__iexact='paid'),
        invoice_due_date__range=[today - timezone.timedelta(days=90), today - timezone.timedelta(days=30)]
    ).count()
    low_risk = all_records.filter(
        ~Q(payment_status__iexact='paid'),
        invoice_due_date__gt=today - timezone.timedelta(days=30),
        invoice_due_date__lt=today
    ).count()

    # --- Employee-wise Summary ---
    all_users = User.objects.all().order_by('username')
    employee_data = []

    for user_obj in all_users:
        profile = UserProfile.objects.filter(user=user_obj).first()

        # Count records uploaded/managed by this user (via employee_name field or created_by)
        user_followups = FollowUp.objects.filter(created_by=user_obj)
        
        employee_data.append({
            'user': user_obj,
            'profile': profile,
            'is_superuser': user_obj.is_superuser,
            'is_staff': user_obj.is_staff,
            'date_joined': user_obj.date_joined,
            'last_login': user_obj.last_login,
            'followup_count': user_followups.count(),
            'email_sent': user_followups.filter(followup_type='Email').count(),
            'whatsapp_sent': user_followups.filter(followup_type='WhatsApp').count(),
            'calls_made': user_followups.filter(followup_type='Call').count(),
        })

    # --- Top Employees by Activity ---
    top_employees = sorted(employee_data, key=lambda x: x['followup_count'], reverse=True)[:10]

    # --- Today's Activity ---
    today_followups = FollowUp.objects.filter(followup_date=today).count()
    emails_today = FollowUp.objects.filter(followup_type='Email', followup_date=today).count()
    whatsapp_today = FollowUp.objects.filter(followup_type='WhatsApp', followup_date=today).count()
    calls_today = FollowUp.objects.filter(followup_type='Call', followup_date=today).count()

    # Revenue trend
    revenue_trend = list(
        all_records
        .annotate(month=TruncMonth('invoice_date'))
        .values('month')
        .annotate(total=Sum('invoice_amount'))
        .order_by('month')[:6]
    )
    for item in revenue_trend:
        if item['month']:
            item['month'] = item['month'].strftime('%b %Y')

    # Top customers
    top_customers = list(
        all_records.values('customer_name')
        .annotate(total_balance=Sum('balance_amount'))
        .order_by('-total_balance')[:10]
    )

    context = {
        'total_stats': total_stats,
        'status_counts': status_counts,
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'employee_data': employee_data,
        'top_employees': top_employees,
        'total_employees': all_users.count(),
        'today_followups': today_followups,
        'emails_today': emails_today,
        'whatsapp_today': whatsapp_today,
        'calls_today': calls_today,
        'revenue_trend': revenue_trend,
        'top_customers': top_customers,
        'today': today,
    }

    return render(request, 'superadmin/dashboard.html', context)


@login_required(login_url='/superadmin/login/')
@user_passes_test(is_superadmin, login_url='/superadmin/login/')
def superadmin_employee_detail_view(request, user_id):
    """Drill-down view for a specific employee — shows all their activity"""
    employee = get_object_or_404(User, pk=user_id)
    today = timezone.localdate()

    profile = UserProfile.objects.filter(user=employee).first()

    # All follow-ups created by this employee
    followups = FollowUp.objects.filter(created_by=employee).select_related('application').order_by('-followup_date', '-created_at')

    followup_stats = followups.aggregate(
        total=Count('id'),
        emails=Count('id', filter=Q(followup_type='Email')),
        whatsapp=Count('id', filter=Q(followup_type='WhatsApp')),
        calls=Count('id', filter=Q(followup_type='Call')),
        ptp=Count('id', filter=Q(followup_type='PTP')),
        completed=Count('id', filter=Q(status='Completed')),
        pending=Count('id', filter=Q(status='Pending')),
    )

    # Recent followups (last 50)
    recent_followups = followups[:50]

    context = {
        'employee': employee,
        'profile': profile,
        'followup_stats': followup_stats,
        'recent_followups': recent_followups,
        'today': today,
    }

    return render(request, 'superadmin/employee_detail.html', context)
