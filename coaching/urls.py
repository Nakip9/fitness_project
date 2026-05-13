"""
URL patterns for the Coaching Management System API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'coaching'

# API URL patterns
api_urlpatterns = [
    # Coach management
    path('coaches/', views.CoachListView.as_view(), name='coach-list'),
    path('coaches/<int:pk>/', views.CoachDetailView.as_view(), name='coach-detail'),
    
    # Coach availability
    path('coaches/<int:coach_id>/availability/', 
         views.CoachAvailabilityListView.as_view(), 
         name='coach-availability-list'),
    path('coaches/<int:coach_id>/availability/<int:pk>/', 
         views.CoachAvailabilityDetailView.as_view(), 
         name='coach-availability-detail'),
    
    # Membership management
    path('memberships/', views.MembershipListView.as_view(), name='membership-list'),
    path('memberships/<int:pk>/', views.MembershipDetailView.as_view(), name='membership-detail'),
    
    # Session management
    path('sessions/', views.CoachingSessionListView.as_view(), name='session-list'),
    path('sessions/<int:pk>/', views.CoachingSessionDetailView.as_view(), name='session-detail'),
    path('sessions/check-conflict/', views.check_schedule_conflict, name='check-schedule-conflict'),
    path('sessions/<int:session_id>/reschedule/', views.reschedule_session, name='reschedule-session'),
    path('sessions/<int:session_id>/checkin/', views.session_checkin, name='session-checkin'),
    path('sessions/<int:session_id>/checkout/', views.session_checkout, name='session-checkout'),
    
    # Session feedback
    path('sessions/<int:session_id>/feedback/', 
         views.SessionFeedbackListView.as_view(), 
         name='session-feedback-list'),
    
    # Membership notes and communication
    path('memberships/<int:membership_id>/notes/', 
         views.MembershipNotesListView.as_view(), 
         name='membership-notes-list'),
    path('notes/<int:pk>/', 
         views.MembershipNoteDetailView.as_view(), 
         name='membership-note-detail'),
    path('notes/<int:note_id>/pin/', views.pin_note, name='pin-note'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/read/', 
         views.mark_notification_read, 
         name='mark-notification-read'),
]

urlpatterns = [
    path('api/', include(api_urlpatterns)),
]