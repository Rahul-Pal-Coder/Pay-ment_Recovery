from django.urls import path
from .views import (
    DashboardListView,
    LoanApplicationCreateView,
    LoanApplicationDetailView,
    LoanApplicationUpdateView,
    LoanApplicationCreateIndividualView,
    LoanApplicationDeleteView,
    save_current_batch,
    send_notifications_view,
    AboutListView,
    ContactListView,
    bulk_send_notifications,
    bulk_edit_records,
    signup_view,
    login_view,
    logout_view,
    clear_all_records,
    superadmin_dashboard,
    view_all_batches,
    view_batch_details,
    add_followup,
    update_followup_status,
)

app_name = "notifications"

urlpatterns = [
    path("", signup_view, name="signup"),
    path("dashboard/", DashboardListView.as_view(), name="dashboard"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("new/", LoanApplicationCreateView.as_view(), name="create"),
    path("add/", LoanApplicationCreateIndividualView.as_view(), name="add"),
    path("record/<int:pk>/", LoanApplicationDetailView.as_view(), name="detail"),
    path("record/<int:pk>/edit/", LoanApplicationUpdateView.as_view(), name="update"),
    path("delete/<int:pk>/", LoanApplicationDeleteView.as_view(), name="delete"),
    path("record/<int:pk>/send/", send_notifications_view, name="send"),
    path("bulk-send/", bulk_send_notifications, name="bulk_send"),
    path("bulk-edit/", bulk_edit_records, name="bulk_edit"),
    path("save-batch/", save_current_batch, name="save_batch"),
    path("clear-all/", clear_all_records, name="clear_all"),
    path("view-batches/", view_all_batches, name="view_batches"),
    path("batch/<int:batch_number>/", view_batch_details, name="batch_details"),
    path("about/", AboutListView.as_view(), name="about"),
    path("contact/", ContactListView.as_view(), name="contact"),
    path("record/<int:pk>/add-followup/", add_followup, name="add_followup"),
    path("followup/<int:pk>/update/", update_followup_status, name="update_followup_status"),
    path(
    "superadmin/",
    superadmin_dashboard,
    name="superadmin_dashboard"
),
]