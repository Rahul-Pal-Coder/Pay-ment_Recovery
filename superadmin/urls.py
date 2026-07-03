from django.urls import path
from . import views

app_name = "superadmin"

urlpatterns = [
    path("login/", views.superadmin_login_view, name="login"),
    path("logout/", views.superadmin_logout_view, name="logout"),
    path("dashboard/", views.superadmin_dashboard_view, name="dashboard"),
    path("employee/<int:user_id>/", views.superadmin_employee_detail_view, name="employee_detail"),
]
