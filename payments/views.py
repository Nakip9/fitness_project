from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import ManualPaymentLog

@login_required
def request_history(request):
    """Requirement 5: Display log of manual payments."""
    payments = ManualPaymentLog.objects.filter(user=request.user).order_by("-transaction_date")
    return render(request, "payments/request_history.html", {"payments": payments})
