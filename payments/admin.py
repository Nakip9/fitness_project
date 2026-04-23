from django.contrib import admin
from .models import ManualPaymentLog

@admin.register(ManualPaymentLog)
class ManualPaymentLogAdmin(admin.ModelAdmin):
    list_display = ("membership", "user", "amount", "transaction_date")
    list_filter = ("transaction_date",)
    search_fields = ("user__username", "membership__trainee__username")
