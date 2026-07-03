@echo off
cd /d "C:\Users\DELL\Desktop\Pay_Ment_Recovery\whatsapp_all_is_perfect\whatsapp"
call .venv\Scripts\activate
celery -A config worker --loglevel=info --pool=solo