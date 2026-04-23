from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import LoginForm, RegistrationForm


class GymfitLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm


class GymfitLogoutView(LogoutView):
    next_page = reverse_lazy("core:home")


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to the club! Your account has been created.")
            return redirect("core:home")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})
