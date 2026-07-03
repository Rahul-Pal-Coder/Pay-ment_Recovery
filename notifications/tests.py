from datetime import date
from io import BytesIO
from decimal import Decimal

from openpyxl import Workbook
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import LoanApplication
from .services import build_email_message, build_whatsapp_message


class NotificationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.record = LoanApplication.objects.create(
            company="Mahima",
            invoice_no="INV-1001",
            invoice_date=date(2026, 4, 1),
            customer_name="Rahul Kumar",
            invoice_due_date=date(2026, 4, 30),
            invoice_amount=Decimal("50000.00"),
            received_amount=Decimal("5000.00"),
            balance_amount=Decimal("45000.00"),
            payment_status="pending",
            whatsapp="+919999999999",
            email="rahul@example.com",
        )

    def test_dashboard_loads(self):
        response = self.client.get(reverse("notifications:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_create_page_loads(self):
        response = self.client.get(reverse("notifications:create"))
        self.assertEqual(response.status_code, 200)

    def test_excel_upload_creates_records(self):
        excel_file = self._build_excel_file(
            [
                {
                    "Invoice No": "INV-2001",
                    "Invoice Date": "2026-05-01",
                    "Customer Name": "Amit",
                    "Invoice Amount": 20000,
                    "Received Amount": 2500,
                    "Balance Amount": 17500,
                    "Due Date": "2026-05-10",
                    "PAYMENT STATUS": "pending",
                    "whatsapp": "+919111111111",
                    "email": "amit@example.com",
                    "Credit Term": "30 Days",
                }
            ]
        )

        response = self.client.post(
            reverse("notifications:create"),
            {
                "excel_file": excel_file,
                "company": "Vincit"
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(LoanApplication.objects.filter(invoice_no="INV-2001").exists())
        record = LoanApplication.objects.get(invoice_no="INV-2001")
        self.assertEqual(record.company, "Vincit")

    def test_excel_upload_deletes_old_records_and_creates_new(self):
        excel_file = self._build_excel_file(
            [
                {
                    "Invoice No": "INV-3001",
                    "Invoice Date": "2026-05-01",
                    "Customer Name": "Rajesh",
                    "Invoice Amount": 30000,
                    "Received Amount": 30000,
                    "Balance Amount": 0,
                    "Due Date": "2026-05-15",
                    "PAYMENT STATUS": "paid",
                    "whatsapp": "+919222222222",
                    "email": "rajesh@example.com",
                }
            ]
        )

        response = self.client.post(
            reverse("notifications:create"),
            {
                "excel_file": excel_file,
                "company": "Mahima"
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(LoanApplication.objects.filter(invoice_no="INV-1001").exists())
        self.assertTrue(LoanApplication.objects.filter(invoice_no="INV-3001").exists())

    def test_excel_upload_ignores_update_and_mail_done_columns(self):
        excel_file = self._build_excel_file(
            [
                {
                    "Invoice No": "INV-4001",
                    "Invoice Date": "2026-05-01",
                    "Customer Name": "Vincit Customer",
                    "Invoice Amount": 30000,
                    "AMOUNT RECEIVED": 10000,
                    "Balance Amount": 20000,
                    "Due Date": "2026-05-15",
                    "PAYMENT STATUS": "pending",
                    "MAIL DONE": "yes",
                    "UPDATE": "follow up",
                    "RTO": "45 Days",
                }
            ]
        )

        response = self.client.post(
            reverse("notifications:create"),
            {
                "excel_file": excel_file,
                "company": "Vincit"
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        record = LoanApplication.objects.get(invoice_no="INV-4001")
        self.assertEqual(record.company, "Vincit")
        self.assertEqual(record.received_amount, Decimal("10000.00"))
        self.assertEqual(record.credit_term, "45 Days")
        self.assertIn(record.email, ("", None))

    def test_messages_include_amount_received_and_rto(self):
        self.record.credit_term = "30 Days RTO"
        self.record.save()

        html_message, text_message = build_email_message(self.record)
        whatsapp_message = build_whatsapp_message(self.record)

        self.assertIn("Amount Received", html_message)
        self.assertIn("Credit Term / RTO", html_message)
        self.assertIn("Rs. 5,000.00", text_message)
        self.assertIn("30 Days RTO", text_message)
        self.assertIn("*Amount Received:* Rs. 5,000.00", whatsapp_message)
        self.assertIn("*Credit Term / RTO:* 30 Days RTO", whatsapp_message)

    @override_settings(
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
        TWILIO_ACCOUNT_SID="",
        TWILIO_AUTH_TOKEN="",
    )
    def test_send_notification_without_credentials(self):
        response = self.client.post(reverse("notifications:send", args=[self.record.pk]), {"channel": "email"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "credentials missing")

    def _build_excel_file(self, rows):
        output = BytesIO()
        workbook = Workbook()
        worksheet = workbook.active
        headers = list(rows[0].keys())
        worksheet.append(headers)
        for row in rows:
            worksheet.append([row.get(header) for header in headers])
        workbook.save(output)
        output.seek(0)
        return SimpleUploadedFile(
            "records.xlsx",
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
