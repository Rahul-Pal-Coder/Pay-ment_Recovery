import json
from django.http import JsonResponse
from django.contrib import messages
from django.db import models
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView, UpdateView, CreateView, DeleteView, TemplateView
from datetime import datetime
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import user_passes_test, login_required
from datetime import timedelta
from django.contrib.auth.models import User
from .forms import ExcelUploadForm, LoanApplicationForm, CustomUserCreationForm
from .models import LoanApplication, LoanApplicationArchive, UserProfile, ExcelBatch, FollowUp
from .services import (
    ExcelImportError,
    NotificationError,
    import_loan_applications_from_excel,
    send_record_notifications,
    send_email_notification,
    send_whatsapp_notification,
    build_message,
)

from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render


class DashboardListView(ListView):
    model = LoanApplication
    template_name = "notifications/dashboard.html"
    context_object_name = "applications"
    paginate_by = 50  # Show 50 records per page

    def parse_date(self, date_str):
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        return None

    def get_queryset(self):
        # Show ALL active records
        queryset = LoanApplication.objects.filter(is_active=True)
        
        search = self.request.GET.get("search", "").strip()
        status = self.request.GET.get("status", "").strip().lower()
        filter_type = self.request.GET.get("filter_type", "").strip()
        month_year = self.request.GET.get("month_year", "").strip()
        year_filter = self.request.GET.get("year", "").strip()
        start_date = self.request.GET.get("start_date", "").strip()
        end_date = self.request.GET.get("end_date", "").strip()

        # Search
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(invoice_no__icontains=search) |
                Q(item_name__icontains=search) |
                Q(employee_name__icontains=search)
            )

        # Status filter
        if status:
            if status == 'overdue':
                queryset = queryset.filter(
                    ~Q(payment_status__iexact='paid'),
                    invoice_due_date__lt=timezone.localdate()
                )
            elif status == 'paid':
                queryset = queryset.filter(payment_status__iexact='paid')
            elif status == 'pending':
                queryset = queryset.filter(
                    ~Q(payment_status__iexact='paid'),
                    invoice_due_date__gte=timezone.localdate()
                )
            else:
                queryset = queryset.filter(payment_status__iexact=status)

        # Monthly filter
        if filter_type == "monthly" and month_year:
            try:
                if "-" in month_year:
                    parts = month_year.split("-")
                    if len(parts[0]) == 4:
                        year = int(parts[0])
                        month = int(parts[1])
                    else:
                        month = int(parts[0])
                        year = int(parts[1])
                    queryset = queryset.filter(
                        invoice_due_date__year=year,
                        invoice_due_date__month=month
                    )
            except:
                pass

        # Yearly filter
        elif filter_type == "yearly" and year_filter:
            try:
                year = int(year_filter)
                queryset = queryset.filter(invoice_due_date__year=year)
            except:
                pass

        # Date range filter
        elif filter_type == "date_range" and start_date and end_date:
            try:
                start = self.parse_date(start_date)
                end = self.parse_date(end_date)
                if start and end:
                    queryset = queryset.filter(invoice_due_date__range=[start, end])
            except:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        queryset = self.get_queryset()
        today = timezone.localdate()
        
        # Stats
        stats = queryset.aggregate(
            total_records=Count("id"),
            total_invoice_amount=Sum("invoice_amount"),
            total_received=Sum("received_amount"),
            total_balance=Sum("balance_amount"),
        )
        
        # All active records stats
        all_active = LoanApplication.objects.filter(is_active=True)
        all_stats = all_active.aggregate(
            all_total_records=Count("id"),
            all_total_invoice_amount=Sum("invoice_amount"),
            all_total_balance=Sum("balance_amount"),
        )
        
        # Status counts
        status_counts = queryset.aggregate(
            paid_count=Count("id", filter=Q(payment_status__iexact="paid")),
            pending_count=Count("id", filter=~Q(payment_status__iexact="paid") & Q(invoice_due_date__gte=today)),
            overdue_count=Count("id", filter=~Q(payment_status__iexact="paid") & Q(invoice_due_date__lt=today)),
        )
        
        # Recovery Risk Category Counts
        high_risk_count = queryset.filter(
            ~Q(payment_status__iexact="paid"),
            invoice_due_date__lt=today - timezone.timedelta(days=90)
        ).count()
        medium_risk_count = queryset.filter(
            ~Q(payment_status__iexact="paid"),
            invoice_due_date__range=[today - timezone.timedelta(days=90), today - timezone.timedelta(days=30)]
        ).count()
        low_risk_count = queryset.filter(
            ~Q(payment_status__iexact="paid"),
            invoice_due_date__gt=today - timezone.timedelta(days=30)
        ).count()

        # Advanced cards data
        today_followups_count = FollowUp.objects.filter(followup_date=today).count()
        pending_calls_count = FollowUp.objects.filter(followup_type='Call', status='Pending').count()
        ptp_due_today_count = FollowUp.objects.filter(followup_type='PTP', ptp_date=today, status='Pending').count()
        emails_sent_today_count = FollowUp.objects.filter(followup_type='Email', followup_date=today).count()
        whatsapp_sent_today_count = FollowUp.objects.filter(followup_type='WhatsApp', followup_date=today).count()
        
        recovered_this_month = LoanApplication.objects.filter(
            is_active=True,
            payment_status__iexact="paid",
            updated_at__year=today.year,
            updated_at__month=today.month
        ).aggregate(Sum('received_amount'))['received_amount__sum'] or 0

        today_followups_list = FollowUp.objects.filter(followup_date=today).select_related('application')[:10]

        # Aging Report buckets
        aging_data = {
            'current': queryset.filter(~Q(payment_status__iexact='paid') & Q(invoice_due_date__gte=today)).aggregate(count=Count('id'), total=Sum('balance_amount')),
            'aging_1_30': queryset.filter(~Q(payment_status__iexact='paid') & Q(invoice_due_date__lt=today) & Q(invoice_due_date__gte=today - timezone.timedelta(days=30))).aggregate(count=Count('id'), total=Sum('balance_amount')),
            'aging_31_60': queryset.filter(~Q(payment_status__iexact='paid') & Q(invoice_due_date__lt=today - timezone.timedelta(days=30)) & Q(invoice_due_date__gte=today - timezone.timedelta(days=60))).aggregate(count=Count('id'), total=Sum('balance_amount')),
            'aging_61_90': queryset.filter(~Q(payment_status__iexact='paid') & Q(invoice_due_date__lt=today - timezone.timedelta(days=60)) & Q(invoice_due_date__gte=today - timezone.timedelta(days=90))).aggregate(count=Count('id'), total=Sum('balance_amount')),
            'aging_90_plus': queryset.filter(~Q(payment_status__iexact='paid') & Q(invoice_due_date__lt=today - timezone.timedelta(days=90))).aggregate(count=Count('id'), total=Sum('balance_amount')),
        }
        
        for k in aging_data:
            if aging_data[k]['total'] is None:
                aging_data[k]['total'] = 0
            if aging_data[k]['count'] is None:
                aging_data[k]['count'] = 0

        # Top customers
        top_customers = list(queryset.values('customer_name')
                            .annotate(total_balance=Sum('balance_amount'))
                            .order_by('-total_balance')[:5])
        
        # Revenue trend
        revenue_trend = list(queryset.annotate(month=TruncMonth('invoice_date'))
                            .values('month')
                            .annotate(total=Sum('invoice_amount'))
                            .order_by('month')[:6])
        
        for item in revenue_trend:
            if item['month']:
                item['month'] = item['month'].strftime('%b %Y')
        
        context.update({
            "stats": stats,
            "all_stats": all_stats,
            "status_counts": status_counts,
            "top_customers": top_customers,
            "revenue_trend": revenue_trend,
            "today": today,
            "selected_status": self.request.GET.get("status", ""),
            "search_query": self.request.GET.get("search", ""),
            "filter_type": self.request.GET.get("filter_type", ""),
            "month_year": self.request.GET.get("month_year", ""),
            "year_filter": self.request.GET.get("year", ""),
            "start_date": self.request.GET.get("start_date", ""),
            "end_date": self.request.GET.get("end_date", ""),
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "low_risk_count": low_risk_count,
            "today_followups_count": today_followups_count,
            "pending_calls_count": pending_calls_count,
            "ptp_due_today_count": ptp_due_today_count,
            "emails_sent_today_count": emails_sent_today_count,
            "whatsapp_sent_today_count": whatsapp_sent_today_count,
            "recovered_this_month": recovered_this_month,
            "today_followups_list": today_followups_list,
            "aging_data": aging_data,
        })
        
        return context


class LoanApplicationCreateView(FormView):
    form_class = ExcelUploadForm
    template_name = "notifications/form.html"
    success_url = reverse_lazy('notifications:dashboard')

    def form_valid(self, form):
        excel_file = form.cleaned_data["excel_file"]
        company = form.cleaned_data.get("company", "Mahima")
        
        # OPTION 1: Delete all old records (hard delete)
        old_count = LoanApplication.objects.all().count()
        LoanApplication.objects.all().delete()
        
        excel_file.seek(0)
        
        try:
            result = import_loan_applications_from_excel(excel_file, company=company)
        except ExcelImportError as exc:
            messages.error(self.request, f"Import failed: {str(exc)}")
            return redirect(self.success_url)
        
        if result["created_count"] > 0:
            messages.success(
                self.request,
                f"✅ {old_count} old records deleted. {result['created_count']} new records imported successfully for {company}."
            )
        else:
            messages.warning(
                self.request,
                f"⚠️ {old_count} old records deleted, but no new records imported. Check Excel file format."
            )
        
        if result["errors"]:
            for error in result["errors"][:5]:
                messages.warning(self.request, error)
        
        return redirect(self.success_url)

    def form_invalid(self, form):
        if "excel_file" in form.errors:
            messages.error(self.request, form.errors["excel_file"][0])
        else:
            messages.error(self.request, "Koi Excel file upload nahi ki gayi.")
        return redirect(self.success_url)


class LoanApplicationUpdateView(UpdateView):
    model = LoanApplication
    form_class = LoanApplicationForm
    template_name = "notifications/form.html"
    success_url = reverse_lazy('notifications:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Record successfully updated.")
        return super().form_valid(form)


class LoanApplicationDetailView(DetailView):
    model = LoanApplication
    template_name = "notifications/detail.html"
    context_object_name = "application"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['followups'] = self.object.followups.all().order_by('-followup_date', '-created_at')
        context['followup_types'] = FollowUp.FOLLOWUP_TYPES
        context['status_choices'] = FollowUp.STATUS_CHOICES
        return context


class LoanApplicationCreateIndividualView(CreateView):
    model = LoanApplication
    form_class = LoanApplicationForm
    template_name = "notifications/form.html"
    success_url = reverse_lazy('notifications:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "✅ New record successfully added.")
        return super().form_valid(form)


class LoanApplicationDeleteView(DeleteView):
    model = LoanApplication
    template_name = "notifications/confirm_delete.html"
    success_url = reverse_lazy('notifications:dashboard')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj_name = str(obj)
        messages.success(request, f"✅ Record '{obj_name}' successfully deleted.")
        return super().delete(request, *args, **kwargs)


class AboutListView(TemplateView):
    template_name = "notifications/about.html"


class ContactListView(TemplateView):
    template_name = "notifications/contact.html"


# @require_POST
# @csrf_protect
# def send_notifications_view(request, pk):
#     application = get_object_or_404(LoanApplication, pk=pk)
#     sender_name = request.POST.get("sender_name", "").strip() or None
#     channel = request.POST.get("channel", "both")
#     custom_message = request.POST.get("custom_message", "").strip() or None
#     user = request.user if request.user.is_authenticated else None
#     user_id = user.id if user else None

#     try:
#         from .tasks import send_single_notification_task, run_task_in_background
#         run_task_in_background(
#             send_single_notification_task,
#             application.id,
#             channel,
#             custom_message=custom_message,
#             sender_name=sender_name,
#             user_id=user_id
#         )
#         messages.success(request, f"🚀 Notification is being sent in the background!")
#     except Exception as exc:
#         messages.error(request, f"❌ Failed to start background task: {str(exc)}")

#     return redirect("notifications:detail", pk=pk)

@require_POST
@csrf_protect
def send_notifications_view(request, pk):
    application = get_object_or_404(LoanApplication, pk=pk)
    
    sender_name = request.POST.get("sender_name", "").strip() or None
    sender_company = request.POST.get("sender_company", "").strip()
    if not sender_company and sender_name:
        if 'vincit' in sender_name.lower():
            sender_company = 'Vincit'
        elif 'mahima' in sender_name.lower() or 'mahim' in sender_name.lower():
            sender_company = 'Mahima'
            
    if not sender_company:
        sender_company = application.company or "Mahima"
    
    channel = request.POST.get("channel", "both")
    custom_message = request.POST.get("custom_message", "").strip() or None
    user = request.user if request.user.is_authenticated else None
    user_id = user.id if user else None

    try:
        from .tasks import send_single_notification_task, run_task_in_background
        run_task_in_background(
            send_single_notification_task,
            application.id,
            channel,
            custom_message=custom_message,
            sender_name=sender_name,
            sender_company=sender_company,
            user_id=user_id
        )
        messages.success(request, f"🚀 Notification sending started using {sender_company} credentials!")
    except Exception as exc:
        messages.error(request, f"❌ Failed to start background task: {str(exc)}")

    return redirect("notifications:detail", pk=pk)

@require_POST
@csrf_protect
def bulk_send_notifications(request):
    try:
        data = json.loads(request.POST.get('filter_data', '{}'))
        notification_type = data.get('type', 'email')
        sender_name = data.get('sender_name', '').strip() or None
        sender_company = data.get('sender_company', '').strip() or None
        
        # Derive sender_company from sender_name if not directly provided
        if not sender_company and sender_name:
            if 'vincit' in sender_name.lower():
                sender_company = 'Vincit'
            elif 'mahima' in sender_name.lower() or 'mahim' in sender_name.lower():
                sender_company = 'Mahima'
                
        custom_message = data.get('custom_message', '').strip() or None
        
        # --- SELECTED IDs LOGIC ---
        # If the user selected specific records, send ONLY to those
        selected_ids = data.get('selected_ids', [])
        
        if selected_ids:
            # Convert to ints, filter only active records
            try:
                selected_ids = [int(i) for i in selected_ids]
            except (ValueError, TypeError):
                selected_ids = []
            
            queryset = LoanApplication.objects.filter(is_active=True, pk__in=selected_ids)
            total_records = queryset.count()
            
            if total_records == 0:
                messages.error(request, "Selected records not found or already archived.")
                return redirect('notifications:dashboard')
            
            application_ids = list(queryset.values_list('id', flat=True))
        else:
            # No selection — apply filters to all active records
            search = data.get('search', '').strip()
            status = data.get('status', '').strip()
            filter_type = data.get('filter_type', '').strip()
            month_year = data.get('month_year', '').strip()
            year_filter = data.get('year', '').strip()
            start_date = data.get('start_date', '').strip()
            end_date = data.get('end_date', '').strip()
            
            queryset = LoanApplication.objects.filter(is_active=True)
            
            # Search
            if search:
                queryset = queryset.filter(
                    Q(customer_name__icontains=search) |
                    Q(invoice_no__icontains=search) |
                    Q(item_name__icontains=search) |
                    Q(employee_name__icontains=search)
                )

            # Status filter
            if status:
                status = status.lower()
                if status == 'overdue':
                    queryset = queryset.filter(
                        ~Q(payment_status__iexact='paid'),
                        invoice_due_date__lt=timezone.localdate()
                    )
                elif status == 'paid':
                    queryset = queryset.filter(payment_status__iexact='paid')
                elif status == 'pending':
                    queryset = queryset.filter(
                        ~Q(payment_status__iexact='paid'),
                        invoice_due_date__gte=timezone.localdate()
                    )
                else:
                    queryset = queryset.filter(payment_status__iexact=status)

            # Monthly filter
            if filter_type == "monthly" and month_year:
                try:
                    if "-" in month_year:
                        parts = month_year.split("-")
                        if len(parts[0]) == 4:
                            year = int(parts[0])
                            month = int(parts[1])
                        else:
                            month = int(parts[0])
                            year = int(parts[1])
                        queryset = queryset.filter(
                            invoice_due_date__year=year,
                            invoice_due_date__month=month
                        )
                except:
                    pass

            # Yearly filter
            elif filter_type == "yearly" and year_filter:
                try:
                    year = int(year_filter)
                    queryset = queryset.filter(invoice_due_date__year=year)
                except:
                    pass

            # Date range filter
            elif filter_type == "date_range" and start_date and end_date:
                try:
                    def parse_date(date_str):
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                            try:
                                return datetime.strptime(date_str, fmt).date()
                            except:
                                continue
                        return None
                    start = parse_date(start_date)
                    end = parse_date(end_date)
                    if start and end:
                        queryset = queryset.filter(invoice_due_date__range=[start, end])
                except:
                    pass
            
            total_records = queryset.count()
            
            if total_records == 0:
                messages.error(request, "No records found with current filter")
                return redirect('notifications:dashboard')
            
            application_ids = list(queryset.values_list('id', flat=True))
        user = request.user if request.user.is_authenticated else None
        user_id = user.id if user else None

        from .tasks import send_bulk_notifications_task, run_task_in_background
        run_task_in_background(
            send_bulk_notifications_task,
            application_ids,
            notification_type,
            custom_message=custom_message,
            sender_name=sender_name,
            sender_company=sender_company,  # Pass company
            user_id=user_id
        )
        messages.success(request, f"🚀 Bulk {notification_type.upper()} dispatch started for {total_records} records using {sender_company or 'Mahima'} credentials!")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")

    return redirect('notifications:dashboard')

@require_POST
@csrf_protect
def bulk_edit_records(request):
    """Bulk edit selected records — only updates fields that are non-empty."""
    try:
        record_ids = request.POST.getlist('record_ids')
        if not record_ids:
            return JsonResponse({'success': False, 'error': 'No records selected.'})

        # Build update dict — only include fields that were actually submitted
        allowed_fields = [
            'company', 'customer_name', 'whatsapp', 'email', 
            'invoice_no', 'invoice_date', 'invoice_due_date', 
            'invoice_amount', 'received_amount', 'balance_amount', 
            'overdue_days', 'payment_status', 'comments',
            'item_name', 'item_sales_qty', 'item_sales_uom', 'item_rate', 'item_amount',
            'employee_name', 'credit_term'
        ]
        update_data = {}
        for field in allowed_fields:
            val = request.POST.get(field, '').strip()
            if val:
                # Type conversions if necessary
                if field in ['invoice_amount', 'received_amount', 'balance_amount', 'item_sales_qty', 'item_rate', 'item_amount']:
                    try:
                        update_data[field] = float(val)
                    except ValueError:
                        pass
                elif field in ['overdue_days']:
                    try:
                        update_data[field] = int(val)
                    except ValueError:
                        pass
                else:
                    update_data[field] = val

        if not update_data:
            return JsonResponse({'success': False, 'error': 'Koi bhi field fill nahi kiya.'})

        # Perform the bulk update only on the selected IDs
        updated = LoanApplication.objects.filter(
            pk__in=record_ids,
            is_active=True
        ).update(**update_data)

        return JsonResponse({'success': True, 'updated': updated})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def clear_all_records(request):
    count = LoanApplication.objects.filter(is_active=True).count()
    LoanApplication.objects.filter(is_active=True).update(
        is_active=False,
        deleted_at=timezone.now()
    )
    messages.success(request, f"✅ {count} records backup Successfully deleted.")
    return redirect('notifications:dashboard')


@require_POST
def save_current_batch(request):
    active_records = LoanApplication.objects.filter(is_active=True)
    count = active_records.count()
    
    if count == 0:
        messages.warning(request, "No records to save.")
        return redirect('notifications:dashboard')
    
    last_batch = LoanApplicationArchive.objects.aggregate(max_batch=models.Max('batch_number'))['max_batch'] or 0
    next_batch = last_batch + 1
    
    saved = 0
    for record in active_records:
        try:
            LoanApplicationArchive.objects.create(
                batch_number=next_batch,
                company=record.company,
                invoice_no=record.invoice_no,
                invoice_date=record.invoice_date,
                customer_name=record.customer_name,
                item_name=record.item_name,
                item_sales_qty=record.item_sales_qty,
                item_sales_uom=record.item_sales_uom,
                item_rate=record.item_rate,
                item_amount=record.item_amount,
                employee_name=record.employee_name,
                credit_term=record.credit_term,
                invoice_due_date=record.invoice_due_date,
                invoice_amount=record.invoice_amount,
                received_amount=record.received_amount,
                balance_amount=record.balance_amount,
                overdue_days=record.overdue_days,
                payment_status=record.payment_status,
                whatsapp=record.whatsapp,
                email=record.email,
                comments=record.comments,
                archived_by=request.user.username if request.user.is_authenticated else 'system'
            )
            saved += 1
        except Exception as e:
            print(f"Error: {e}")
    
    messages.success(request, f"✅ {saved} records saved as Batch #{next_batch}")
    return redirect('notifications:view_batches')


def view_all_batches(request):
    batches = LoanApplicationArchive.objects.values('batch_number').annotate(
        total_records=models.Count('id'),
        total_amount=models.Sum('invoice_amount'),
        first_upload=models.Min('archived_at')
    ).order_by('-batch_number')
    
    context = {
        'batches': batches,
        'total_batches': batches.count(),
        'total_records': LoanApplicationArchive.objects.count(),
    }
    return render(request, 'notifications/batches_list.html', context)


def view_batch_details(request, batch_number):
    records = LoanApplicationArchive.objects.filter(batch_number=batch_number)
    
    if not records.exists():
        messages.warning(request, f"Batch #{batch_number} not found.")
        return redirect('notifications:view_batches')
    
    context = {
        'records': records,
        'batch_number': batch_number,
        'total_records': records.count(),
        'total_amount': records.aggregate(total=models.Sum('invoice_amount'))['total'] or 0,
    }
    return render(request, 'notifications/batch_details.html', context)


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('notifications:dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.signup_time = timezone.now()
            profile.save()
            messages.success(request, "Signup successful!")
            return redirect('notifications:dashboard')
        else:
            for error in form.errors.values():
                messages.error(request, error)
            return render(request, 'notifications/signup.html', {'form': form})
    else:
        form = CustomUserCreationForm()
        return render(request, 'notifications/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('notifications:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.last_login_time = timezone.now()
                profile.save()
                messages.success(request, f"Welcome back {username}!")
                return redirect('notifications:dashboard')
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'notifications/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('notifications:login')


@login_required
@require_POST
def add_followup(request, pk):
    application = get_object_or_404(LoanApplication, pk=pk)
    followup_type = request.POST.get('followup_type', 'Call')
    followup_date_str = request.POST.get('followup_date', '')
    status = request.POST.get('status', 'Pending')
    ptp_amount_str = request.POST.get('ptp_amount', '')
    ptp_date_str = request.POST.get('ptp_date', '')
    notes = request.POST.get('notes', '')
    
    today = timezone.localdate()
    followup_date = today
    if followup_date_str:
        try:
            followup_date = datetime.strptime(followup_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    ptp_date = None
    if ptp_date_str and followup_type == 'PTP':
        try:
            ptp_date = datetime.strptime(ptp_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    ptp_amount = None
    if ptp_amount_str and followup_type == 'PTP':
        try:
            ptp_amount = float(ptp_amount_str)
        except ValueError:
            pass
            
    FollowUp.objects.create(
        application=application,
        followup_type=followup_type,
        followup_date=followup_date,
        status=status,
        ptp_amount=ptp_amount,
        ptp_date=ptp_date,
        notes=notes,
        created_by=request.user
    )
    
    messages.success(request, f"✅ Follow-up log created successfully!")
    return redirect('notifications:detail', pk=pk)


@login_required
@require_POST
def update_followup_status(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    status = request.POST.get('status', 'Completed')
    if status in ['Pending', 'Completed', 'Cancelled']:
        followup.status = status
        followup.save()
        messages.success(request, f"✅ Follow-up status updated to {status}!")
    return redirect('notifications:detail', pk=followup.application.pk)

@user_passes_test(lambda u: u.is_superuser)
def superadmin_dashboard(request):
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    all_employees = User.objects.filter(is_active=True)
    employee_performance = []
    
    for employee in all_employees:
        # Today's followups attributed to this employee:
        # 1. Directly created by them (created_by=employee)
        # 2. Older system-created ones where application.employee_name matches (created_by=None)
        today_followups = FollowUp.objects.filter(
            Q(created_by=employee) |
            Q(created_by=None, application__employee_name__iexact=employee.username),
            followup_date=today
        )

        # PTP count for today (by ptp_date)
        today_ptp_count = FollowUp.objects.filter(
            Q(created_by=employee) |
            Q(created_by=None, application__employee_name__iexact=employee.username),
            followup_type='PTP',
            ptp_date=today,
        ).count()

        employee_performance.append({
            'employee': employee,
            'today': {
                'total': today_followups.count(),
                'calls': today_followups.filter(followup_type='Call').count(),
                'emails': today_followups.filter(followup_type='Email').count(),
                'whatsapp': today_followups.filter(followup_type='WhatsApp').count(),
                'ptp': today_ptp_count,
                'completed': today_followups.filter(status='Completed').count(),
            },
            'weekly': {
                'total': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'calls': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='Call', followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'emails': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='Email', followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'whatsapp': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='WhatsApp', followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'ptp': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='PTP', ptp_date__gte=start_of_week, ptp_date__lte=today).count(),
            },
            'monthly': {
                'total': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'calls': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='Call', followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'emails': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='Email', followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'whatsapp': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='WhatsApp', followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'ptp': FollowUp.objects.filter(Q(created_by=employee) | Q(created_by=None, application__employee_name__iexact=employee.username), followup_type='PTP', ptp_date__gte=start_of_month, ptp_date__lte=today).count(),
            },
            'recovered_amount': (
                FollowUp.objects.filter(
                    Q(created_by=employee) |
                    Q(created_by=None, application__employee_name__iexact=employee.username),
                    followup_type='PTP',
                    status='Completed'
                ).aggregate(total=Sum('ptp_amount'))['total'] or 0
            ) + (
                LoanApplication.objects.filter(
                    employee_name__iexact=employee.username,
                    payment_status='paid'
                ).aggregate(total=Sum('received_amount'))['total'] or 0
            ),
        })

    employee_performance.sort(key=lambda x: x['today']['total'], reverse=True)
    
    # Rest of your code remains same...
    today_followups_detail = FollowUp.objects.filter(
        followup_date=today
    ).select_related('created_by', 'application').order_by('-created_at')
    
    # Today's PTP list (for PTP tab)
    today_ptp_list = FollowUp.objects.filter(
        followup_type='PTP',
        ptp_date=today,
        status='Pending'
    ).select_related('created_by', 'application')
    
    upcoming_ptp_list = FollowUp.objects.filter(
        followup_type='PTP',
        ptp_date__gt=today,
        ptp_date__lte=today + timedelta(days=7),
        status='Pending'
    ).select_related('created_by', 'application').order_by('ptp_date')
    
    completed_ptp_list = FollowUp.objects.filter(
        followup_type='PTP',
        status='Completed'
    ).select_related('created_by', 'application').order_by('-ptp_date')[:20]
    
    pending_followups = FollowUp.objects.filter(
        status='Pending',
        followup_date__lte=today
    ).select_related('created_by', 'application').order_by('followup_date')[:30]
    
    # Compute totals directly from DB (includes created_by=None system records too)
    total_today_followups = FollowUp.objects.filter(followup_date=today).count()
    total_today_calls = FollowUp.objects.filter(followup_type='Call', followup_date=today).count()
    total_today_emails = FollowUp.objects.filter(followup_type='Email', followup_date=today).count()
    total_today_whatsapp = FollowUp.objects.filter(followup_type='WhatsApp', followup_date=today).count()
    total_today_ptp = FollowUp.objects.filter(followup_type='PTP', ptp_date=today).count()

    context = {
        'employee_performance': employee_performance,
        'total_today_followups': total_today_followups,
        'total_today_calls': total_today_calls,
        'total_today_emails': total_today_emails,
        'total_today_whatsapp': total_today_whatsapp,
        'total_today_ptp': total_today_ptp,
        'total_employees': all_employees.count(),
        'active_employees': len([e for e in employee_performance if e['today']['total'] > 0]),
        'today_ptp_list': today_ptp_list,
        'upcoming_ptp_list': upcoming_ptp_list,
        'completed_ptp_list': completed_ptp_list,
        'today_followups_detail': today_followups_detail,
        'pending_followups': pending_followups,
        'today': today,
        'start_of_week': start_of_week,
        'start_of_month': start_of_month,
    }

    return render(request, 'notifications/superadmin_dashboard.html', context)
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    # ========== GET ALL ACTIVE EMPLOYEES ==========
    all_employees = User.objects.filter(is_active=True)
    
    # ========== BUILD PERFORMANCE DATA FOR ALL EMPLOYEES ==========
    employee_performance = []
    
    for employee in all_employees:
        # ✅ FIX: Sirf wahi followups jinka followup_date today hai
        today_followups = FollowUp.objects.filter(
            created_by=employee,
            followup_date=today
        )
        
        # ✅ DEBUG: Print for each employee
        print(f"\n--- Employee: {employee.username} ---")
        print(f"Total followups today: {today_followups.count()}")
        print(f"PTP count (from filter): {today_followups.filter(followup_type='PTP').count()}")
        
        # ✅ Alternative: Direct PTP count for this employee today
        direct_ptp_count = FollowUp.objects.filter(
            created_by=employee,
            followup_date=today,
            followup_type='PTP'
        ).count()
        print(f"Direct PTP count: {direct_ptp_count}")
        
        # Count by type
        ptp_count = today_followups.filter(followup_type='PTP').count()
        
        employee_performance.append({
            'employee': employee,
            'today': {
                'total': today_followups.count(),
                'calls': today_followups.filter(followup_type='Call').count(),
                'emails': today_followups.filter(followup_type='Email').count(),
                'whatsapp': today_followups.filter(followup_type='WhatsApp').count(),
                'ptp': ptp_count,  # PTP count
                'completed': today_followups.filter(status='Completed').count(),
            },
            'weekly': {
                'total': FollowUp.objects.filter(created_by=employee, followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'calls': FollowUp.objects.filter(created_by=employee, followup_type='Call', followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'emails': FollowUp.objects.filter(created_by=employee, followup_type='Email', followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'whatsapp': FollowUp.objects.filter(created_by=employee, followup_type='WhatsApp', followup_date__gte=start_of_week, followup_date__lte=today).count(),
                'ptp': FollowUp.objects.filter(created_by=employee, followup_type='PTP', followup_date__gte=start_of_week, followup_date__lte=today).count(),
            },
            'monthly': {
                'total': FollowUp.objects.filter(created_by=employee, followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'calls': FollowUp.objects.filter(created_by=employee, followup_type='Call', followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'emails': FollowUp.objects.filter(created_by=employee, followup_type='Email', followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'whatsapp': FollowUp.objects.filter(created_by=employee, followup_type='WhatsApp', followup_date__gte=start_of_month, followup_date__lte=today).count(),
                'ptp': FollowUp.objects.filter(created_by=employee, followup_type='PTP', followup_date__gte=start_of_month, followup_date__lte=today).count(),
            },
            'recovered_amount': LoanApplication.objects.filter(
                employee_name=employee.username,
                payment_status='paid'
            ).aggregate(total=Sum('received_amount'))['total'] or 0,
        })
    
    # Sort by today's performance
    employee_performance.sort(key=lambda x: x['today']['total'], reverse=True)
    
    # ========== TODAY'S FOLLOWUPS DETAILS ==========
    today_followups_detail = FollowUp.objects.filter(
        followup_date=today
    ).select_related('created_by', 'application').order_by('-created_at')
    
    # ========== PTP DETAILS ==========
    # Today's PTP (based on ptp_date, not followup_date)
    today_ptp_list = FollowUp.objects.filter(
        followup_type='PTP',
        ptp_date=today,
        status='Pending'
    ).select_related('created_by', 'application')
    
    print(f"\n=== FINAL PTP COUNT IN PERFORMANCE ===")
    for emp in employee_performance:
        print(f"{emp['employee'].username}: PTP = {emp['today']['ptp']}")
    
    print(f"\n=== TODAY'S PTP LIST (based on ptp_date) ===")
    print(f"Count: {today_ptp_list.count()}")
    for ptp in today_ptp_list:
        print(f"  - {ptp.application.customer_name} by {ptp.created_by.username}")
    
    # Upcoming PTP
    upcoming_ptp_list = FollowUp.objects.filter(
        followup_type='PTP',
        ptp_date__gt=today,
        ptp_date__lte=today + timedelta(days=7),
        status='Pending'
    ).select_related('created_by', 'application').order_by('ptp_date')
    
    # Completed PTP
    completed_ptp_list = FollowUp.objects.filter(
        followup_type='PTP',
        status='Completed'
    ).select_related('created_by', 'application').order_by('-ptp_date')[:20]
    
    # Pending followups
    pending_followups = FollowUp.objects.filter(
        status='Pending',
        followup_date__lte=today
    ).select_related('created_by', 'application').order_by('followup_date')[:30]
    
    # Calculate totals
    total_today_followups = sum(p['today']['total'] for p in employee_performance)
    total_today_calls = sum(p['today']['calls'] for p in employee_performance)
    total_today_emails = sum(p['today']['emails'] for p in employee_performance)
    total_today_whatsapp = sum(p['today']['whatsapp'] for p in employee_performance)
    total_today_ptp = sum(p['today']['ptp'] for p in employee_performance)
    
    context = {
        'employee_performance': employee_performance,
        'total_today_followups': total_today_followups,
        'total_today_calls': total_today_calls,
        'total_today_emails': total_today_emails,
        'total_today_whatsapp': total_today_whatsapp,
        'total_today_ptp': total_today_ptp,
        'total_employees': all_employees.count(),
        'active_employees': len([e for e in employee_performance if e['today']['total'] > 0]),
        
        # PTP Details
        'today_ptp_list': today_ptp_list,
        'upcoming_ptp_list': upcoming_ptp_list,
        'completed_ptp_list': completed_ptp_list,
        
        'today_followups_detail': today_followups_detail,
        'pending_followups': pending_followups,
        
        'today': today,
        'start_of_week': start_of_week,
        'start_of_month': start_of_month,
    }
    
    return render(request, 'notifications/superadmin_dashboard.html', context)