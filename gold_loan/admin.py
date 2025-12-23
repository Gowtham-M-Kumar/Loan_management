from django.contrib import admin
from .models import (
    Customer,
    Loan,
    GoldItem,
    GoldItemImage,
    LoanDocument,
    Payment,
    LoanExpense
)

# =========================
# INLINE MODELS
# =========================

class GoldItemImageInline(admin.TabularInline):
    model = GoldItemImage
    extra = 0


class GoldItemInline(admin.TabularInline):
    model = GoldItem
    extra = 0


class LoanDocumentInline(admin.TabularInline):
    model = LoanDocument
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("total_amount", "interest_component", "principal_component", "payment_date", "payment_mode")


class LoanExpenseInline(admin.TabularInline):
    model = LoanExpense
    extra = 0


# =========================
# CUSTOMER ADMIN
# =========================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "customer_id",
        "name",
        "mobile_primary",
        "aadhaar_number",
        "profession",
        "nominee_name",
    )

    search_fields = (
        "customer_id",
        "name",
        "mobile_primary",
        "aadhaar_number",
    )

    list_filter = ("profession",)

    ordering = ("-id",)


# =========================
# LOAN ADMIN
# =========================

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "loan_number",
        "lot_number",
        "customer",
        "total_amount",
        "pending_interest",
        "status",
        "loan_start_date",
        "last_capitalization_date",
        "created_at",
    )

    search_fields = (
        "loan_number",
        "lot_number",
        "customer__name",
        "customer__customer_id",
        "customer__mobile_primary",
    )

    list_filter = ("status", "created_at", "loan_start_date")

    readonly_fields = ("lot_number", "loan_number", "created_at", "updated_at")

    ordering = ("-created_at",)

    fieldsets = (
        ("Basic Info", {
            "fields": ("loan_number", "lot_number", "customer", "status")
        }),
        ("Amount & Terms", {
            "fields": ("total_amount", "interest_rate", "price_per_gram", "approved_grams", "pending_interest")
        }),
        ("Critical Dates", {
            "fields": ("loan_start_date", "interest_lock_until", "last_interest_calculated_at", "last_capitalization_date", "closed_at")
        }),
        ("Structure", {
            "fields": ("parent_loan", "created_at", "updated_at")
        }),
        ("Bank / Pledge Details", {
            "fields": ("bank_name", "bank_address", "pledge_receipt_no", "pledge_notes")
        }),
    )

    inlines = [
        GoldItemInline,
        LoanDocumentInline,
        PaymentInline,
        LoanExpenseInline,
    ]


# =========================
# GOLD ITEM ADMIN
# =========================

@admin.register(GoldItem)
class GoldItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "loan",
        "carat",
        "gross_weight",
        "approved_net_weight",
    )

    list_filter = ("carat",)

    inlines = [GoldItemImageInline]


# =========================
# LOAN DOCUMENT ADMIN
# =========================

@admin.register(LoanDocument)
class LoanDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "loan",
        "document_type",
        "other_name",
    )


# =========================
# PAYMENT ADMIN
# =========================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "loan",
        "total_amount",
        "interest_component",
        "principal_component",
        "payment_date",
        "payment_mode",
    )
    
    list_filter = ("payment_date", "payment_mode")
    search_fields = ("loan__loan_number", "loan__customer__name", "reference_no")
    ordering = ("-created_at",)


# =========================
# LOAN EXPENSE ADMIN
# =========================

@admin.register(LoanExpense)
class LoanExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "loan",
        "amount",
        "medium",
        "date",
    )
    
    list_filter = ("date", "medium")
    search_fields = ("loan__loan_number", "notes")
    ordering = ("-created_at",)
