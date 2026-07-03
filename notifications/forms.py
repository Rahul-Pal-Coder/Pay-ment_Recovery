from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import LoanApplication


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField()
    company = forms.ChoiceField(
        choices=[('Mahima', 'Mahima'), ('Vincit', 'Vincit')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='Mahima',
        label="Select Excel Type"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["excel_file"].widget.attrs.update(
            {
                "class": "form-control",
                "accept": ".xlsx,.csv",
            }
        )


class LoanApplicationForm(forms.ModelForm):
    invoice_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    invoice_due_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = LoanApplication
        fields = [
            "company",
            "invoice_no",
            "invoice_date",
            "customer_name",
            "item_name",
            "item_sales_qty",
            "item_sales_uom",
            "item_rate",
            "item_amount",
            "employee_name",
            "credit_term",
            "invoice_due_date",
            "invoice_amount",
            "received_amount",
            "balance_amount",
            "overdue_days",
            "payment_status",
            "whatsapp",
            "email",
            "comments",
        ]
        widgets = {
            "item_name": forms.TextInput(attrs={"placeholder": "Item name"}),
            "customer_name": forms.TextInput(attrs={"placeholder": "Customer name"}),
            "comments": forms.Textarea(attrs={"rows": 3, "placeholder": "Enter comments here..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-control"
            if isinstance(field.widget, forms.Select):
                css_class = "form-select"
            field.widget.attrs["class"] = css_class

    def clean(self):
        cleaned_data = super().clean()
        payment_status = cleaned_data.get("payment_status")
        invoice_amount = cleaned_data.get("invoice_amount")
        received_amount = cleaned_data.get("received_amount", 0)
        
        # Auto-calculate balance amount
        if invoice_amount and received_amount is not None:
            cleaned_data["balance_amount"] = invoice_amount - received_amount
        
        # Validate payment status
        if payment_status == "paid" and cleaned_data.get("balance_amount", 0) > 0:
            self.add_error("payment_status", "Paid status mein balance amount zero hona chahiye.")

        return cleaned_data


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]   # ✅ FIX
        if commit:
            user.save()
        return user
