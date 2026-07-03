# Loan Notification App

Ye Django application customer loan/order record save karta hai aur WhatsApp plus email notification bhejne ke liye ready hai.

## Features

- Customer name, email, WhatsApp number, address
- Loan ID, order ID, loan amount, installment amount
- Due date aur payment date tracking
- Payment status: Pending, Paid, Overdue
- Bootstrap dashboard with search and filter
- Twilio WhatsApp integration
- SMTP email integration

## Setup

1. `python -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `.env.example` ko copy karke `.env` banaiye aur apne credentials daliye
5. `python manage.py makemigrations`
6. `python manage.py migrate`
7. `python manage.py runserver`

## WhatsApp Integration

- Twilio account banaiye
- Twilio WhatsApp Sandbox enable kariye
- `.env` me `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` set kariye
- Recipient number international format me daliye, jaise `+919876543210`

## Email Integration

- Gmail ya kisi SMTP provider ka use kar sakte hain
- Gmail ke liye App Password use kariye
- `.env` me `EMAIL_HOST_USER` aur `EMAIL_HOST_PASSWORD` bharna zaroori hai

## URLs

- Dashboard: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## Important

Credentials na hone par app chalega, lekin notification button result me batayega ki credentials missing hain.
