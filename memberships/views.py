from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView
from django.views.decorators.http import require_POST
from django.db import transaction
from datetime import timedelta

from .forms import MembershipContactForm
from .models import TrainingPlan, Membership, MembershipNote, AuditLog


class MembershipPlanListView(ListView):
    template_name = "memberships/plan_list.html"
    queryset = TrainingPlan.objects.all()
    context_object_name = "plans"


class MembershipPlanDetailView(DetailView):
    template_name = "memberships/plan_detail.html"
    model = TrainingPlan
    context_object_name = "plan"


@login_required
def subscribe(request, pk):
    """Instant Activation Flow: User chooses tier and protocol starts immediately."""
    plan = get_object_or_404(TrainingPlan, pk=pk)
    
    if request.method == "POST":
        start_date = timezone.now()
        end_date = start_date + timedelta(days=plan.duration_days)

        # Create the membership in ACTIVE state immediately
        membership = Membership.objects.create(
            trainee=request.user,
            plan=plan,
            status=Membership.Status.ACTIVE,
            payment_status=Membership.PaymentStatus.PAID,
            scheduled_start=start_date,
            scheduled_end=end_date
        )
        
        # Save initial goals as a note
        goals = request.POST.get("goals", "")
        if goals:
            MembershipNote.objects.create(
                membership=membership,
                author=request.user,
                content=f"Initial Goals: {goals}"
            )
            
        AuditLog.objects.create(
            membership=membership,
            actor=request.user,
            action="INSTANT_ACTIVATION",
            new_state={"status": "ACTIVE", "start": str(start_date)}
        )

        messages.success(request, f"Your {plan.name} protocol has started! Check your email for details.")
        return redirect("memberships:my_memberships")
        
    return render(request, "memberships/subscribe.html", {"plan": plan})


@login_required
def my_memberships(request):
    """Requirement 2: Full Client Visibility & Real-Time UI."""
    memberships = Membership.objects.filter(trainee=request.user).select_related('plan', 'coach').prefetch_related('comms_hub', 'audit_trail')
    return render(request, "memberships/my_memberships.html", {"memberships": memberships})


@login_required
def activate_plan(request, membership_id):
    """Fallback for manual approval if needed."""
    membership = get_object_or_404(Membership, id=membership_id, trainee=request.user)
    
    if membership.status == Membership.Status.APPROVED:
        start_date = timezone.now()
        membership.scheduled_start = start_date
        membership.scheduled_end = start_date + timedelta(days=membership.plan.duration_days)
        membership.status = Membership.Status.ACTIVE
        membership.payment_status = Membership.PaymentStatus.PAID
        membership.save()
        messages.success(request, "Protocol activated.")
    
    return redirect("memberships:my_memberships")


@login_required
@require_POST
def add_note(request, membership_id):
    """Requirement 6: Interactive Notes & Replies."""
    membership = get_object_or_404(Membership, id=membership_id)
    
    if request.user != membership.trainee and request.user != membership.coach:
        return redirect("core:home")

    content = request.POST.get("content")
    parent_id = request.POST.get("parent_id")
    
    if content:
        parent_note = None
        if parent_id:
            parent_note = MembershipNote.objects.filter(id=parent_id).first()

        MembershipNote.objects.create(
            membership=membership,
            author=request.user,
            content=content,
            parent=parent_note,
            is_coach_note=(request.user == membership.coach)
        )
        messages.success(request, "Note recorded.")
    return redirect("memberships:my_memberships")


@login_required
def update_status(request, membership_id, status):
    """Requirement 4: Plan Lifecycle Management."""
    membership = get_object_or_404(Membership, id=membership_id, trainee=request.user)
    
    status_map = {
        'CANCELLED': Membership.Status.CANCELLED,
        'POSTPONED': Membership.Status.POSTPONED,
        'PAUSED': Membership.Status.PAUSED,
        'ACTIVE': Membership.Status.ACTIVE,
    }
    
    new_status = status_map.get(status.upper())
    if new_status:
        old_status = membership.get_status_display()
        membership.status = new_status
        membership.save()
        
        AuditLog.objects.create(
            membership=membership,
            actor=request.user,
            action="TRAINEE_LIFECYCLE_CHANGE",
            old_state={"status": old_status},
            new_state={"status": membership.get_status_display()}
        )
        messages.success(request, f"Status updated to {membership.get_status_display()}.")
        
    return redirect("memberships:my_memberships")


@login_required
def update_schedule(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id, trainee=request.user)
    
    if request.method == "POST":
        start_str = request.POST.get("start_time")
        end_str = request.POST.get("end_time")
        
        if start_str and end_str:
            old_start = membership.scheduled_start
            membership.scheduled_start = start_str
            membership.scheduled_end = end_str
            
            try:
                membership.full_clean()
                membership.save()
                messages.success(request, "Schedule updated!")
            except Exception as e:
                messages.error(request, f"Conflict: {e}")
                
    return redirect("memberships:my_memberships")
