"""
Django Admin configuration for the Coaching Management System
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    Coach, CoachAvailability, CoachingSession, SessionAttendance,
    SessionFeedback, EnhancedMembershipNote, NotificationLog
)


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'specialization', 'hourly_rate', 'is_active', 'created_at']
    list_filter = ['is_active', 'specialization', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'specialization']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'specialization', 'bio')
        }),
        ('Professional Details', {
            'fields': ('hourly_rate', 'max_daily_sessions', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'


class CoachAvailabilityInline(admin.TabularInline):
    model = CoachAvailability
    extra = 0
    fields = ['day_of_week', 'start_time', 'end_time', 'is_active']


@admin.register(CoachAvailability)
class CoachAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['coach', 'day_of_week', 'start_time', 'end_time', 'is_active']
    list_filter = ['day_of_week', 'is_active', 'coach']
    search_fields = ['coach__user__first_name', 'coach__user__last_name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('coach__user')


class SessionAttendanceInline(admin.StackedInline):
    model = SessionAttendance
    extra = 0
    fields = ['status', 'check_in_time', 'check_out_time', 'notes']


class SessionFeedbackInline(admin.TabularInline):
    model = SessionFeedback
    extra = 0
    readonly_fields = ['author', 'created_at']
    fields = ['author', 'content', 'rating', 'is_coach_feedback', 'created_at']


@admin.register(CoachingSession)
class CoachingSessionAdmin(admin.ModelAdmin):
    list_display = [
        'trainee_name', 'coach', 'scheduled_start', 'scheduled_end', 
        'status', 'duration_display', 'created_at'
    ]
    list_filter = ['status', 'coach', 'scheduled_start', 'created_at']
    search_fields = [
        'membership__user__first_name', 'membership__user__last_name',
        'coach__user__first_name', 'coach__user__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'duration_minutes', 'is_past_due']
    date_hierarchy = 'scheduled_start'
    inlines = [SessionAttendanceInline, SessionFeedbackInline]
    
    fieldsets = (
        ('Session Information', {
            'fields': ('membership', 'coach', 'status')
        }),
        ('Scheduling', {
            'fields': ('scheduled_start', 'scheduled_end', 'actual_start', 'actual_end')
        }),
        ('Session Details', {
            'fields': ('session_notes', 'coach_feedback', 'trainee_feedback', 'rating')
        }),
        ('Computed Fields', {
            'fields': ('duration_minutes', 'is_past_due'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'membership__user', 'coach__user'
        )
    
    def trainee_name(self, obj):
        return obj.membership.user.get_full_name() or obj.membership.user.username
    trainee_name.short_description = 'Trainee'
    
    def duration_display(self, obj):
        return f"{obj.duration_minutes} min"
    duration_display.short_description = 'Duration'
    
    def view_membership_link(self, obj):
        url = reverse('admin:memberships_membership_change', args=[obj.membership.pk])
        return format_html('<a href="{}">View Membership</a>', url)
    view_membership_link.short_description = 'Membership'


@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    list_display = ['session_info', 'status', 'check_in_time', 'check_out_time', 'was_late']
    list_filter = ['status', 'session__scheduled_start']
    search_fields = [
        'session__membership__user__first_name',
        'session__membership__user__last_name'
    ]
    readonly_fields = ['was_late', 'minutes_late']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'session__membership__user', 'session__coach__user'
        )
    
    def session_info(self, obj):
        return f"{obj.session.membership.user.get_full_name()} - {obj.session.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
    session_info.short_description = 'Session'


@admin.register(SessionFeedback)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = ['session_info', 'author', 'rating', 'is_coach_feedback', 'created_at']
    list_filter = ['is_coach_feedback', 'rating', 'created_at']
    search_fields = [
        'session__membership__user__first_name',
        'session__membership__user__last_name',
        'author__first_name', 'author__last_name'
    ]
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'session__membership__user', 'author'
        )
    
    def session_info(self, obj):
        return f"{obj.session.membership.user.get_full_name()} - {obj.session.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
    session_info.short_description = 'Session'


@admin.register(EnhancedMembershipNote)
class EnhancedMembershipNoteAdmin(admin.ModelAdmin):
    list_display = ['membership_info', 'author', 'is_pinned', 'is_reply', 'created_at']
    list_filter = ['is_pinned', 'created_at', 'author']
    search_fields = [
        'membership__user__first_name', 'membership__user__last_name',
        'author__first_name', 'author__last_name', 'content'
    ]
    readonly_fields = ['created_at', 'updated_at', 'is_coach_note']
    
    fieldsets = (
        ('Note Information', {
            'fields': ('membership', 'author', 'content')
        }),
        ('Threading', {
            'fields': ('parent_note', 'is_pinned')
        }),
        ('Metadata', {
            'fields': ('is_coach_note', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'membership__user', 'author'
        )
    
    def membership_info(self, obj):
        return f"{obj.membership.user.get_full_name()} - {obj.membership.plan.name}"
    membership_info.short_description = 'Membership'
    
    def is_reply(self, obj):
        return obj.parent_note is not None
    is_reply.boolean = True
    is_reply.short_description = 'Reply'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'email_sent', 'is_read', 'created_at']
    list_filter = ['notification_type', 'email_sent', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'title', 'message']
    readonly_fields = ['created_at', 'is_read_display']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        ('Delivery Status', {
            'fields': ('email_sent', 'read_at', 'is_read_display')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def is_read_display(self, obj):
        return obj.read_at is not None
    is_read_display.boolean = True
    is_read_display.short_description = 'Read'
    
    actions = ['mark_as_read', 'resend_notification']
    
    def mark_as_read(self, request, queryset):
        updated = 0
        for notification in queryset:
            if not notification.read_at:
                notification.mark_as_read()
                updated += 1
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
    
    def resend_notification(self, request, queryset):
        # This would integrate with your email service
        count = queryset.count()
        self.message_user(request, f'{count} notifications queued for resending.')
    resend_notification.short_description = 'Resend selected notifications'


# Customize the admin site header
admin.site.site_header = "Coaching Management System"
admin.site.site_title = "Coaching Admin"
admin.site.index_title = "Welcome to Coaching Management System"