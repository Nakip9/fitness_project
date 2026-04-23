from django.urls import path
from . import views

app_name = "memberships"

urlpatterns = [
    path("", views.MembershipPlanListView.as_view(), name="plan_list"),
    path("my/", views.my_memberships, name="my_memberships"),
    path("<int:pk>/", views.MembershipPlanDetailView.as_view(), name="plan_detail"),
    path("<int:pk>/subscribe/", views.subscribe, name="subscribe"),
    
    # Comms & Lifecycle
    path("note/add/<int:membership_id>/", views.add_note, name="add_note"),
    path("status/update/<int:membership_id>/<str:status>/", views.update_status, name="update_status"),
    path("schedule/update/<int:membership_id>/", views.update_schedule, name="update_schedule"),
    path("activate/<int:membership_id>/", views.activate_plan, name="activate_plan"),
]
