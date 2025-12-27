from django.urls import path
from . import views

app_name = "gold_loan"

urlpatterns = [
    # Home Page (Landing)
    path("", views.home, name="home"),
    
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    
    # Analytics Dashboard
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),

    # Loan Entry (redirect to step 1)
    path("loan/", views.loan_entry, name="loan_entry"),

    # Loan Entry Steps
    path("loan/entry/step-1/", views.loan_entry_step1, name="loan_entry_step1"),
    path("loan/entry/step-2/", views.loan_entry_step2, name="loan_entry_step2"),
    path("loan/entry/step-3/", views.loan_entry_step3, name="loan_entry_step3"),
    path("loan/entry/step-4/", views.loan_entry_step4, name="loan_entry_step4"),
    path("loan/entry/step-5/", views.loan_entry_step5, name="loan_entry_step5"),
    path("api/resend-otp/", views.resend_otp_api, name="resend_otp_api"),

    # Other Pages
    # Payment
    path("loan/<int:loan_id>/payment/", views.loan_payment_view, name="loan_payment_view"),
    path("payment/", views.payment, name="payment"), # keeping legacy for safety, though functionality moved
    path("closed-loans/", views.closed_loans_list, name="closed_loans_list"),
    path("extended-loans/", views.extended_loans_list, name="extended_loans_list"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/create/", views.customer_create, name="customer_create"),
    path("customers/<int:customer_id>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:customer_id>/edit/", views.customer_edit, name="customer_edit"),
    path("close/", views.loan_close, name="loan_close"),
    
    # API Endpoints
    path("api/search-customers/", views.search_customers, name="search_customers"),
    path("api/get-customer/<int:customer_id>/", views.get_customer, name="get_customer"),

    # Loan View (Read-Only)
    path("loan/<int:loan_id>/view/", views.loan_view, name="loan_view"),
    path("loan/<int:loan_id>/edit/", views.loan_edit, name="loan_edit"),

    # Receipts
    path("loan/<int:loan_id>/receipt/", views.loan_receipt, name="loan_receipt"),
    path("loan/<int:loan_id>/payment-summary-receipt/", views.payment_summary_receipt, name="payment_summary_receipt"),
    path("payment/<int:payment_id>/receipt/", views.payment_receipt, name="payment_receipt"),
    path("loan/<int:loan_id>/closure-receipt/", views.loan_closure_receipt, name="loan_closure_receipt"),

    # Actions
    path("loan/<int:loan_id>/close-action/", views.loan_close_action, name="loan_close_action"),
    path("loan/<int:loan_id>/close-otp/", views.loan_close_otp, name="loan_close_otp"),
    path("loan/<int:loan_id>/close-upload/", views.loan_close_upload, name="loan_close_upload"),
    path("loan/<int:loan_id>/close-confirm/", views.loan_close_confirm, name="loan_close_confirm"),
    path("loan/<int:loan_id>/extend-otp/", views.loan_extend_otp, name="loan_extend_otp"),
    path("loan/<int:loan_id>/extend-action/", views.loan_extend_action, name="loan_extend_action"),
    path("api/loan/<int:loan_id>/simulate-interest/", views.simulate_interest, name="simulate_interest"),
    
    # Reports
    path("analytics/export/", views.export_report, name="export_report"),
]

