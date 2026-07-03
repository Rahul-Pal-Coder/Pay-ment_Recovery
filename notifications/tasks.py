# import logging
# from celery import shared_task
# from django.contrib.auth.models import User
# from .models import LoanApplication
# from .services import send_email_notification, send_whatsapp_notification

# logger = logging.getLogger(__name__)

# @shared_task
# def send_single_notification_task(application_id, channel, custom_message=None, sender_name=None, user_id=None):
#     try:
#         application = LoanApplication.objects.get(pk=application_id)
#     except LoanApplication.DoesNotExist:
#         logger.error(f"LoanApplication with id {application_id} does not exist.")
#         return f"Error: Application {application_id} not found"

#     user = None
#     if user_id:
#         try:
#             user = User.objects.get(pk=user_id)
#         except User.DoesNotExist:
#             logger.warning(f"User with id {user_id} does not exist.")

#     try:
#         if channel == 'email':
#             res = send_email_notification(application, message=custom_message, sender_name=sender_name, user=user)
#             return f"Email sent: {res}"
#         elif channel == 'whatsapp':
#             res = send_whatsapp_notification(application, message=custom_message, sender_name=sender_name, user=user)
#             return f"WhatsApp sent: {res}"
#         else:
#             from .services import send_record_notifications
#             res = send_record_notifications(application, message=custom_message, sender_name=sender_name, user=user)
#             return f"Both sent: {res}"
#     except Exception as exc:
#         logger.exception(f"Error sending notification for application {application_id}")
#         return f"Failed: {str(exc)}"

# @shared_task
# def send_bulk_notifications_task(application_ids, notification_type, custom_message=None, sender_name=None, user_id=None):
#     user = None
#     if user_id:
#         try:
#             user = User.objects.get(pk=user_id)
#         except User.DoesNotExist:
#             logger.warning(f"User with id {user_id} does not exist.")

#     success_count = 0
#     fail_count = 0

#     for app_id in application_ids:
#         try:
#             application = LoanApplication.objects.get(pk=app_id)
#             if notification_type == 'email':
#                 send_email_notification(application, message=custom_message, sender_name=sender_name, user=user)
#             else:
#                 send_whatsapp_notification(application, message=custom_message, sender_name=sender_name, user=user)
#             success_count += 1
#         except Exception as e:
#             logger.exception(f"Error in bulk send for app {app_id}")
#             fail_count += 1

#     return f"Bulk send complete. Success: {success_count}, Failed: {fail_count}"

# def run_task_in_background(task_func, *args, **kwargs):
#     from django import db
#     import threading
    
#     def wrapper():
#         try:
#             task_func(*args, **kwargs)
#         except Exception as e:
#             logger.exception("Error running background task in thread")
#         finally:
#             db.connections.close_all()
            
#     thread = threading.Thread(target=wrapper)
#     thread.daemon = True
#     thread.start()



import threading
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from .models import LoanApplication, FollowUp
from .services import (
    send_email_notification, 
    send_whatsapp_notification, 
    send_record_notifications
)


def run_task_in_background(task_func, *args, **kwargs):
    """
    Run a task in background using threading
    """
    def wrapper():
        try:
            task_func(*args, **kwargs)
        except Exception as e:
            print(f"Error running background task: {str(e)}")
    
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()


@shared_task
def send_single_notification_task(application_id, channel, custom_message=None, sender_name=None, sender_company=None, user_id=None):
    """
    Send single notification to one application
    """
    try:
        application = LoanApplication.objects.get(id=application_id)
    except LoanApplication.DoesNotExist:
        print(f"Application {application_id} not found")
        return
    
    user = None
    if user_id:
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass
    
    if channel == 'email':
        send_email_notification(
            application, 
            message=custom_message, 
            sender_name=sender_name,
            sender_company=sender_company,
            user=user
        )
    elif channel == 'whatsapp':
        send_whatsapp_notification(
            application, 
            message=custom_message, 
            sender_name=sender_name,
            sender_company=sender_company,
            user=user
        )
    else:
        send_record_notifications(
            application, 
            message=custom_message, 
            sender_name=sender_name,
            sender_company=sender_company,
            user=user
        )


@shared_task
def send_bulk_notifications_task(application_ids, notification_type, custom_message=None, sender_name=None, sender_company=None, user_id=None):
    """
    Send bulk notifications to multiple applications
    """
    user = None
    if user_id:
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass
    
    success_count = 0
    fail_count = 0
    
    for app_id in application_ids:
        try:
            application = LoanApplication.objects.get(id=app_id)
            
            if notification_type == 'email':
                result = send_email_notification(
                    application, 
                    message=custom_message, 
                    sender_name=sender_name,
                    sender_company=sender_company,
                    user=user
                )
                if result == "sent":
                    success_count += 1
                else:
                    fail_count += 1
                    
            elif notification_type == 'whatsapp':
                result = send_whatsapp_notification(
                    application, 
                    message=custom_message, 
                    sender_name=sender_name,
                    sender_company=sender_company,
                    user=user
                )
                if result == "sent":
                    success_count += 1
                else:
                    fail_count += 1
                    
        except Exception as e:
            fail_count += 1
            print(f"Error sending to application {app_id}: {str(e)}")
    
    print(f"Bulk send completed: {success_count} success, {fail_count} failed")
    return {"success": success_count, "failed": fail_count}