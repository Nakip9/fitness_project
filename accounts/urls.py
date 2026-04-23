from django.urls import path

from .views import GymfitLoginView, GymfitLogoutView, register

app_name = "accounts"

urlpatterns = [
    path("login/", GymfitLoginView.as_view(), name="login"),
    path("logout/", GymfitLogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
]
