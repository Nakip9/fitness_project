from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("history/", views.request_history, name="history"),
]
