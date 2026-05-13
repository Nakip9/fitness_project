"""
API Views for the Coaching Management System
"""
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from memberships.models import Membership, MembershipPlan
from .models import (
    Coach, CoachAvailability, CoachingSession, SessionAttendance,
    SessionFeedback, EnhancedMembershipNote, NotificationLog
)
from .serializers import (
    CoachSerializer, CoachAvailabilitySerializer, CoachingSessionSerializer,
    CoachingSessionCreateSerializer, SessionAttendanceSerializer,
    SessionFeedbackSerializer, EnhancedMembershipNoteSerializer,
    NotificationLogSerializer, MembershipSerializer, ScheduleConflictSerializer,
    RescheduleSessionSerializer
)
from .permissions import IsCoachOrReadOnly, IsOwnerOrCoach

User = get_user_model()


class CoachListView(generics.ListAPIView):
    """List all active coaches"""
    queryset = Coach.objects.filter(is_active=True).select_related('user')
    serializer_class = CoachSerializer
    permission_classes = [permissions.IsAuthenticated]


class CoachDetailView(generics.RetrieveAPIView):
    """Get coach details"""
    queryset = Coach.objects.filter(is_active=True).select_related('user')
    serializer_class = CoachSerializer
    permission_classes = [permissions.IsAuthenticated]


class CoachAvailabilityListView(generics.ListCreateAPIView):
    """List and create coach availability slots"""
    serializer_class = CoachAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsCoachOrReadOnly]
    
    def get_queryset(self):
        coach_id = self.kwargs['coach_id']
        return CoachAvailability.objects.filter(
            coach_id=coach_id,
            is_active=True
        ).order_by('day_of_week', 'start_time')
    
    def perform_create(self, serializer):
        coach = Coach.objects.get(id=self.kwargs['coach_id'])
        # Only allow coaches to modify their own availability or staff
        if not self.request.user.is_staff and coach.user != self.request.user:
            raise permissions.PermissionDenied("You can only modify your own availability")
        serializer.save(coach=coach)


class CoachAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual availability slots"""
    serializer_class = CoachAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsCoachOrReadOnly]
    
    def get_queryset(self):
        coach_id = self.kwargs['coach_id']
        return CoachAvailability.objects.filter(coach_id=coach_id)
    
    def perform_update(self, serializer):
        availability = self.get_object()
        # Only allow coaches to modify their own availability or staff
        if not self.request.user.is_staff and availability.coach.user != self.request.user:
            raise permissions.PermissionDenied("You can only modify your own availability")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only allow coaches to modify their own availability or staff
        if not self.request.user.is_staff and instance.coach.user != self.request.user:
            raise permissions.PermissionDenied("You can only modify your own availability")
        instance.is_active = False
        instance.save()


class MembershipListView(generics.ListAPIView):
    """List user's memberships"""
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Membership.objects.all().select_related('user', 'plan', 'coach')
        return Membership.objects.filter(user=self.request.user).select_related('plan', 'coach')


class MembershipDetailView(generics.RetrieveUpdateAPIView):
    """Get and update membership details"""
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrCoach]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Membership.objects.all().select_related('user', 'plan', 'coach')
        return Membership.objects.filter(user=self.request.user).select_related('plan', 'coach')


class CoachingSessionListView(generics.ListCreateAPIView):
    """List and create coaching sessions"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CoachingSessionCreateSerializer
        return CoachingSessionSerializer
    
    def get_queryset(self):
        queryset = CoachingSession.objects.select_related(
            'membership__user', 'membership__plan', 'coach__user'
        ).prefetch_related('feedback_entries', 'attendance')
        
        # Filter based on user role
        if self.request.user.is_staff:
            # Staff can see all sessions
            pass
        elif hasattr(self.request.user, 'coach_profile'):
            # Coaches see their own sessions
            queryset = queryset.filter(coach__user=self.request.user)
        else:
            # Regular users see only their sessions
            queryset = queryset.filter(membership__user=self.request.user)
        
        # Apply filters
        coach_id = self.request.query_params.get('coach_id')
        if coach_id:
            queryset = queryset.filter(coach_id=coach_id)
        
        membership_id = self.request.query_params.get('membership_id')
        if membership_id:
            queryset = queryset.filter(membership_id=membership_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Date range filters
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(scheduled_start__gte=start_date)
        if end_date:
            queryset = queryset.filter(scheduled_end__lte=end_date)
        
        return queryset.order_by('-scheduled_start')


class CoachingSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual coaching sessions"""
    serializer_class = CoachingSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrCoach]
    
    def get_queryset(self):
        queryset = CoachingSession.objects.select_related(
            'membership__user', 'membership__plan', 'coach__user'
        ).prefetch_related('feedback_entries', 'attendance')
        
        if self.request.user.is_staff:
            return queryset
        elif hasattr(self.request.user, 'coach_profile'):
            return queryset.filter(coach__user=self.request.user)
        else:
            return queryset.filter(membership__user=self.request.user)
    
    def perform_destroy(self, instance):
        """Cancel session instead of deleting"""
        instance.cancel("Cancelled by user")


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_schedule_conflict(request):
    """Check for scheduling conflicts"""
    serializer = ScheduleConflictSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            coach = Coach.objects.get(id=data['coach_id'])
        except Coach.DoesNotExist:
            return Response(
                {'error': 'Coach not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check availability
        is_available = coach.is_available_at(
            data['start_time'], 
            data['end_time']
        )
        
        conflicts = []
        if not is_available:
            # Get conflicting sessions
            conflicting_sessions = CoachingSession.objects.filter(
                coach=coach,
                status__in=['scheduled', 'confirmed', 'in_progress'],
                scheduled_start__lt=data['end_time'],
                scheduled_end__gt=data['start_time']
            ).select_related('membership__user')
            
            if data.get('exclude_session_id'):
                conflicting_sessions = conflicting_sessions.exclude(
                    id=data['exclude_session_id']
                )
            
            for session in conflicting_sessions:
                conflicts.append({
                    'session_id': session.id,
                    'trainee': session.membership.user.get_full_name(),
                    'start_time': session.scheduled_start,
                    'end_time': session.scheduled_end
                })
        
        return Response({
            'is_available': is_available,
            'conflicts': conflicts
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsOwnerOrCoach])
def reschedule_session(request, session_id):
    """Reschedule a coaching session"""
    try:
        session = CoachingSession.objects.get(id=session_id)
    except CoachingSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if not request.user.is_staff:
        if hasattr(request.user, 'coach_profile'):
            if session.coach.user != request.user:
                return Response(
                    {'error': 'Permission denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        elif session.membership.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    
    serializer = RescheduleSessionSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            with transaction.atomic():
                session.reschedule(
                    data['new_start_time'], 
                    data['new_end_time']
                )
                
                # Create notification
                NotificationLog.objects.create(
                    user=session.membership.user,
                    notification_type='session_rescheduled',
                    title='Session Rescheduled',
                    message=f'Your session has been rescheduled to {data["new_start_time"].strftime("%Y-%m-%d %H:%M")}'
                )
                
                return Response({
                    'message': 'Session rescheduled successfully',
                    'session': CoachingSessionSerializer(session).data
                })
        
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def session_checkin(request, session_id):
    """Check in to a session"""
    try:
        session = CoachingSession.objects.get(id=session_id)
    except CoachingSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only trainee or coach can check in
    if (session.membership.user != request.user and 
        session.coach.user != request.user and 
        not request.user.is_staff):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if session.status != 'scheduled':
        return Response(
            {'error': 'Session is not in scheduled status'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    session.check_in()
    
    # Create or update attendance record
    attendance, created = SessionAttendance.objects.get_or_create(
        session=session,
        defaults={'check_in_time': timezone.now()}
    )
    if not created:
        attendance.check_in_time = timezone.now()
        attendance.save()
    
    return Response({
        'message': 'Checked in successfully',
        'session': CoachingSessionSerializer(session).data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def session_checkout(request, session_id):
    """Check out from a session"""
    try:
        session = CoachingSession.objects.get(id=session_id)
    except CoachingSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only trainee or coach can check out
    if (session.membership.user != request.user and 
        session.coach.user != request.user and 
        not request.user.is_staff):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if session.status != 'in_progress':
        return Response(
            {'error': 'Session is not in progress'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    session.check_out()
    
    # Update attendance record
    try:
        attendance = SessionAttendance.objects.get(session=session)
        attendance.check_out_time = timezone.now()
        attendance.save()
    except SessionAttendance.DoesNotExist:
        SessionAttendance.objects.create(
            session=session,
            check_out_time=timezone.now()
        )
    
    return Response({
        'message': 'Checked out successfully',
        'session': CoachingSessionSerializer(session).data
    })


class SessionFeedbackListView(generics.ListCreateAPIView):
    """List and create session feedback"""
    serializer_class = SessionFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        session_id = self.kwargs['session_id']
        return SessionFeedback.objects.filter(
            session_id=session_id
        ).select_related('author')
    
    def perform_create(self, serializer):
        session_id = self.kwargs['session_id']
        session = CoachingSession.objects.get(id=session_id)
        
        # Check if user is involved in the session
        if (session.membership.user != self.request.user and 
            session.coach.user != self.request.user and 
            not self.request.user.is_staff):
            raise permissions.PermissionDenied("You can only provide feedback for your own sessions")
        
        is_coach_feedback = (
            self.request.user.is_staff or 
            session.coach.user == self.request.user
        )
        
        serializer.save(
            session=session,
            author=self.request.user,
            is_coach_feedback=is_coach_feedback
        )


class MembershipNotesListView(generics.ListCreateAPIView):
    """List and create membership notes"""
    serializer_class = EnhancedMembershipNoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrCoach]
    
    def get_queryset(self):
        membership_id = self.kwargs['membership_id']
        return EnhancedMembershipNote.objects.filter(
            membership_id=membership_id,
            parent_note__isnull=True  # Only top-level notes
        ).select_related('author').prefetch_related('replies__author')
    
    def perform_create(self, serializer):
        membership_id = self.kwargs['membership_id']
        membership = Membership.objects.get(id=membership_id)
        
        # Check permissions
        if not self.request.user.is_staff:
            if membership.user != self.request.user:
                raise permissions.PermissionDenied("You can only add notes to your own memberships")
        
        serializer.save(
            membership=membership,
            author=self.request.user
        )


class MembershipNoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual membership notes"""
    serializer_class = EnhancedMembershipNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EnhancedMembershipNote.objects.select_related('author', 'membership')
    
    def perform_update(self, serializer):
        note = self.get_object()
        # Only author or staff can update notes
        if note.author != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only update your own notes")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only author or staff can delete notes
        if instance.author != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only delete your own notes")
        instance.delete()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pin_note(request, note_id):
    """Pin or unpin a membership note"""
    try:
        note = EnhancedMembershipNote.objects.get(id=note_id)
    except EnhancedMembershipNote.DoesNotExist:
        return Response(
            {'error': 'Note not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only coaches/staff can pin notes
    if not request.user.is_staff:
        return Response(
            {'error': 'Only coaches can pin notes'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if note.is_pinned:
        note.unpin()
        message = 'Note unpinned'
    else:
        note.pin()
        message = 'Note pinned'
    
    return Response({
        'message': message,
        'note': EnhancedMembershipNoteSerializer(note).data
    })


class NotificationListView(generics.ListAPIView):
    """List user notifications"""
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return NotificationLog.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = NotificationLog.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.mark_as_read()
        return Response({'message': 'Notification marked as read'})
    except NotificationLog.DoesNotExist:
        return Response(
            {'error': 'Notification not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )