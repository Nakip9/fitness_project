from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView

# get_object_or_404 is still used by subscribe(); _get_membership_for_user
# handles the staff-aware lookup for all membership-specific views.

from payments.models import PaymentRequest

from .forms import MembershipContactForm
from .models import Membership, MembershipNote, MembershipPlan


class MembershipPlanListView(ListView):
    template_name = "memberships/plan_list.html"
    queryset = MembershipPlan.objects.filter(is_active=True)
    context_object_name = "plans"


class MembershipPlanDetailView(DetailView):
    template_name = "memberships/plan_detail.html"
    model = MembershipPlan
    slug_field = "slug"
    slug_url_kwarg = "slug"
    context_object_name = "plan"


@login_required
def subscribe(request, slug):
    plan = get_object_or_404(MembershipPlan, slug=slug, is_active=True)
    plans = MembershipPlan.objects.filter(is_active=True)
    if request.method == "POST":
        form = MembershipContactForm(request.POST, plans=plans)
        if form.is_valid():
            selected_plan = form.cleaned_data["plan"]
            phone_number = form.cleaned_data["phone_number"]
            membership = (
                Membership.objects.filter(
                    user=request.user,
                    plan=selected_plan,
                    status="pending",
                )
                .order_by("-start_date")
                .first()
            )
            if membership is None:
                membership = Membership.objects.create(
                    user=request.user,
                    plan=selected_plan,
                    start_date=timezone.now(),
                    status="pending",
                )
            PaymentRequest.objects.create(
                user=request.user,
                plan=selected_plan,
                phone_number=phone_number,
                notes=f"Membership #{membership.pk} pending activation",
            )
            messages.success(
                request,
                "Thank you! Our customer service team will contact you within 2 hours to finalize your membership.",
            )
            return redirect("memberships:plan_detail", slug=selected_plan.slug)
    else:
        form = MembershipContactForm(plans=plans, initial_plan=plan)

    selected_plan_value = form["plan"].value() or (str(plans.first().pk) if plans else "")
    return render(
        request,
        "memberships/subscribe.html",
        {
            "plan": plan,
            "plans": plans,
            "form": form,
            "selected_plan": selected_plan_value,
        },
    )


@login_required
def my_memberships(request):
    memberships = Membership.objects.filter(user=request.user).select_related("plan")
    return render(request, "memberships/my_memberships.html", {"memberships": memberships})


def _get_membership_for_user(pk, user):
    """
    Return the Membership with the given pk if the requesting user is allowed
    to access it:
      - Staff / superusers can access any membership.
      - Regular users can only access their own.
    Raises Http404 if not found or not permitted.
    """
    from django.http import Http404

    try:
        membership = Membership.objects.select_related("user", "plan").get(pk=pk)
    except Membership.DoesNotExist:
        raise Http404("No Membership matches the given query.")

    if not user.is_staff and membership.user != user:
        raise Http404("No Membership matches the given query.")

    return membership


@login_required
def membership_detail(request, pk):
    """
    Trainees see only their own membership.
    Staff (coach / admin) can view any membership.
    """
    membership = _get_membership_for_user(pk, request.user)
    notes = membership.notes.select_related("author").all()
    return render(
        request,
        "memberships/membership_detail.html",
        {"membership": membership, "notes": notes},
    )


@login_required
def add_note(request, pk):
    """Allow the membership owner OR any staff member (coach) to add notes."""
    membership = _get_membership_for_user(pk, request.user)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            MembershipNote.objects.create(
                membership=membership,
                author=request.user,
                content=content,
            )
            messages.success(request, "Note added successfully.")
        else:
            messages.error(request, "Note content cannot be empty.")

    return redirect("memberships:membership_detail", pk=pk)


@login_required
def cancel_membership(request, pk):
    """
    Cancel the membership — stops the active countdown.
    Accessible by the membership owner OR staff.
    Only processes on POST; GET redirects back with a warning.
    """
    membership = _get_membership_for_user(pk, request.user)

    if membership.status == "canceled":
        messages.info(request, "This membership is already canceled.")
        return redirect("memberships:membership_detail", pk=pk)

    if request.method == "POST":
        try:
            membership.cancel()
            messages.success(
                request,
                "The membership has been canceled. The countdown has been stopped.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
    else:
        # Somebody navigated here via GET — just bounce back
        messages.warning(request, "Use the Cancel button on the membership page.")

    return redirect("memberships:membership_detail", pk=pk)


@login_required
def postpone_membership(request, pk):
    """
    Postpone the membership — freezes remaining days and hides the session
    window until the coach assigns a new time.
    Accessible by the membership owner OR staff.
    Only processes on POST; GET redirects back with a warning.
    """
    membership = _get_membership_for_user(pk, request.user)

    if membership.status == "postponed":
        messages.info(request, "This membership is already postponed.")
        return redirect("memberships:membership_detail", pk=pk)

    if request.method == "POST":
        try:
            membership.postpone()
            messages.success(
                request,
                f"Membership postponed. "
                f"{membership.postponed_remaining_days} days have been frozen. "
                "The coach will assign a new session time when ready to resume.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
    else:
        messages.warning(request, "Use the Postpone button on the membership page.")

    return redirect("memberships:membership_detail", pk=pk)
