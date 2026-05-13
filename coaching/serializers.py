"""
Django REST Framework serializers for the Coaching Management System
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from memberships.models import Membership, MembershipPlan
from .models import (
    Coach, CoachAvailability, CoachingSession, SessionAttendance,
    SessionFeedback, EnhancedMembershipNote, NotificationLog
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Basic user information"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['id', 'username']


class CoachSerializer(serializers.ModelSerializer):
    """Coach profile serializer"""
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Coach
        fields = [
            'id', 'user', 'full_name', 'specialization', 'bio', 
            'hourly_rate', 'is_active', 'max_daily_sessions', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CoachAvailabilitySerializer(serializers.ModelSerializer):
    """Coach availability serializer"""
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = CoachAvailability
        fields = [
            'id', 'day_of_week', 'day_display', 'start_time', 
            'end_time', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("Start time must be before end time")
        return data


class MembershipPlanSerializer(serializers.ModelSerializer):
    """Membership plan serializer"""
    class Meta:
        model = MembershipPlan
        fields = [
            'id', 'name', 'slug', 'description', 'price', 
            'duration_days', 'billing_cycle', 'is_active', 'featured'
        ]


class MembershipSerializer(serializers.ModelSerializer):
    """Membership serializer with enhanced details"""
    user = UserSerializer(read_only=True)
    plan = MembershipPlanSerializer(read_only=True)
    coach = CoachSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Membership
        fields = [
            'id', 'user', 'plan', 'coach', 'start_date', 'end_date',
            'status', 'status_display', 'auto_renew', 'coach_notes',
            'postponed_remaining_days', 'days_left', 'is_active'
        ]
        read_only_fields = [
            'id', 'user', 'plan', 'start_date', 'end_date', 
            'postponed_remaining_days'
        ]


class SessionAttendanceSerializer(serializers.ModelSerializer):
    """Session attendance serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    was_late = serializers.BooleanField(read_only=True)
    minutes_late = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = SessionAttendance
        fields = [
            'id', 'status', 'status_display', 'check_in_time', 
            'check_out_time', 'notes', 'was_late', 'minutes_late'
        ]


class SessionFeedbackSerializer(serializers.ModelSerializer):
    """Session feedback serializer"""
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = SessionFeedback
        fields = [
            'id', 'author', 'content', 'rating', 
            'is_coach_feedback', 'created_at'
        ]
        read_only_fields = ['id', 'author', 'is_coach_feedback', 'created_at']


class CoachingSessionSerializer(serializers.ModelSerializer):
    """Coaching session serializer with full details"""
    membership = MembershipSerializer(read_only=True)
    coach = CoachSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    is_past_due = serializers.BooleanField(read_only=True)
    attendance = SessionAttendanceSerializer(read_only=True)
    feedback_entries = SessionFeedbackSerializer(many=True, read_only=True)
    
    class Meta:
        model = CoachingSession
        fields = [
            'id', 'membership', 'coach', 'scheduled_start', 'scheduled_end',
            'actual_start', 'actual_end', 'status', 'status_display',
            'session_notes', 'coach_feedback', 'trainee_feedback', 'rating',
            'duration_minutes', 'is_past_due', 'attendance', 'feedback_entries',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'membership', 'coach', 'actual_start', 'actual_end',
            'created_at', 'updated_at'
        ]


class CoachingSessionCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating sessions"""
    membership_id = serializers.IntegerField()
    coach_id = serializers.IntegerField()
    
    class Meta:
        model = CoachingSession
        fields = [
            'membership_id', 'coach_id', 'scheduled_start', 
            'scheduled_end', 'session_notes'
        ]
    
    def validate(self, data):
        # Validate membership exists and belongs to user (if not staff)
        try:
            membership = Membership.objects.get(id=data['membership_id'])
            if not self.context['request'].user.is_staff:
                if membership.user != self.context['request'].user:
                    raise serializers.ValidationError("You can only schedule sessions for your own memberships")
        except Membership.DoesNotExist:
            raise serializers.ValidationError("Membership not found")
        
        # Validate coach exists
        try:
            coach = Coach.objects.get(id=data['coach_id'])
        except Coach.DoesNotExist:
            raise serializers.ValidationError("Coach not found")
        
        # Validate time slot
        if data['scheduled_start'] >= data['scheduled_end']:
            raise serializers.ValidationError("Start time must be before end time")
        
        return data
    
    def create(self, validated_data):
        membership = Membership.objects.get(id=validated_data.pop('membership_id'))
        coach = Coach.objects.get(id=validated_data.pop('coach_id'))
        
        session = CoachingSession.objects.create(
            membership=membership,
            coach=coach,
            **validated_data
        )
        return session


class EnhancedMembershipNoteSerializer(serializers.ModelSerializer):
    """Enhanced membership note serializer with threading"""
    author = UserSerializer(read_only=True)
    is_coach_note = serializers.BooleanField(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = EnhancedMembershipNote
        fields = [
            'id', 'author', 'content', 'is_pinned', 'parent_note',
            'is_coach_note', 'replies', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        if obj.parent_note is None:  # Only get replies for top-level notes
            replies = obj.replies.all()
            return EnhancedMembershipNoteSerializer(replies, many=True, context=self.context).data
        return []


class NotificationLogSerializer(serializers.ModelSerializer):
    """Notification log serializer"""
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification_type', 'type_display', 'title', 
            'message', 'email_sent', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_is_read(self, obj):
        return obj.read_at is not None


class ScheduleConflictSerializer(serializers.Serializer):
    """Serializer for schedule conflict checking"""
    coach_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    exclude_session_id = serializers.IntegerField(required=False)
    
    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("Start time must be before end time")
        return data


class RescheduleSessionSerializer(serializers.Serializer):
    """Serializer for rescheduling sessions"""
    new_start_time = serializers.DateTimeField()
    new_end_time = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500, required=False)
    
    def validate(self, data):
        if data['new_start_time'] >= data['new_end_time']:
            raise serializers.ValidationError("Start time must be before end time")
        return data