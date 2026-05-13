"""
Custom permissions for the Coaching Management System
"""
from rest_framework import permissions


class IsCoachOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow coaches to edit their own data.
    """
    
    def has_permission(self, request, view):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions only for coaches or staff
        return (
            request.user.is_authenticated and 
            (request.user.is_staff or hasattr(request.user, 'coach_profile'))
        )
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for the coach who owns the object or staff
        if request.user.is_staff:
            return True
        
        # Check if user is the coach associated with the object
        if hasattr(obj, 'coach'):
            return obj.coach.user == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsOwnerOrCoach(permissions.BasePermission):
    """
    Custom permission to allow access to owners or their coaches.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff can access everything
        if request.user.is_staff:
            return True
        
        # Check if user owns the object
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Check if user is the coach for this membership/session
        if hasattr(obj, 'membership'):
            # For sessions, check if user is the coach
            if hasattr(obj, 'coach') and obj.coach.user == request.user:
                return True
            # For membership-related objects, check if user owns the membership
            if obj.membership.user == request.user:
                return True
        
        # Check if user is a coach associated with the membership
        if hasattr(obj, 'coach') and obj.coach.user == request.user:
            return True
        
        return False


class IsCoachOnly(permissions.BasePermission):
    """
    Permission class that only allows coaches and staff.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.is_staff or hasattr(request.user, 'coach_profile'))
        )


class IsOwnerOnly(permissions.BasePermission):
    """
    Permission class that only allows owners of the object.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff can access everything
        if request.user.is_staff:
            return True
        
        # Check various ways the user might own the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'author'):
            return obj.author == request.user
        elif hasattr(obj, 'membership') and hasattr(obj.membership, 'user'):
            return obj.membership.user == request.user
        
        return False