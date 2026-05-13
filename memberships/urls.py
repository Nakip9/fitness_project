from django.urls import path

from . import views

app_name = "memberships"

urlpatterns = [
    path("", views.MembershipPlanListView.as_view(), name="plan_list"),
    path("my/", views.my_memberships, name="my_memberships"),
    path("my/<int:pk>/", views.membership_detail, name="membership_detail"),
    path("my/<int:pk>/note/", views.add_note, name="add_note"),
    path("my/<int:pk>/cancel/", views.cancel_membership, name="cancel_membership"),
    path("my/<int:pk>/postpone/", views.postpone_membership, name="postpone_membership"),
    path("<slug:slug>/", views.MembershipPlanDetailView.as_view(), name="plan_detail"),
    path("<slug:slug>/subscribe/", views.subscribe, name="subscribe"),
]
