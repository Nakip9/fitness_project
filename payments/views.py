from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import PaymentRequest


@login_required
def request_history(request):
    requests = PaymentRequest.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "payments/request_history.html", {"requests": requests})
