from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import Membership, MembershipBenefit, MembershipNote, MembershipPlan


class MembershipBenefitInline(admin.TabularInline):
    model = MembershipBenefit
    extra = 1


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "billing_cycle", "is_active", "featured")
    list_filter = ("is_active", "featured", "billing_cycle")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipBenefitInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "colored_status",
        "time_slot_display",
        "days_left_display",
        "start_date",
        "end_date",
    )
    list_filter = ("status", "plan")
    search_fields = ("user__username", "user__first_name", "user__last_name", "plan__name")
    readonly_fields = ("end_date", "days_left_display", "time_slot_display", "postponed_remaining_days")
    ordering = ("-start_date",)

    fieldsets = (
        (
            "Trainee & Plan",
            {
                "fields": ("user", "plan", "status"),
                "description": (
                    "⚠️ Status transitions: Pending → Active (via payment). "
                    "Active → Postponed or Canceled. "
                    "Postponed → Active (re-assigns a new scheduled_time first)."
                ),
            },
        ),
        (
            "Dates",
            {
                "fields": ("start_date", "end_date", "days_left_display"),
            },
        ),
        (
            "Session Scheduling",
            {
                "fields": ("scheduled_time", "duration_minutes", "time_slot_display"),
                "description": (
                    "Set the daily session start time. "
                    "The system will prevent double-booking against other Active memberships."
                ),
            },
        ),
        (
            "Postpone State",
            {
                "fields": ("postponed_remaining_days",),
                "classes": ("collapse",),
                "description": "Automatically populated when a membership is postponed.",
            },
        ),
        (
            "Coach Communication",
            {
                "fields": ("coach_notes",),
                "description": "Permanent sticky instructions shown at the top of the trainee's dashboard.",
            },
        ),
    )

    # ------------------------------------------------------------------
    # Custom display columns
    # ------------------------------------------------------------------

    @admin.display(description="Status")
    def colored_status(self, obj):
        colors = {
            "active": ("#166534", "#dcfce7"),
            "pending": ("#854d0e", "#fef9c3"),
            "postponed": ("#075985", "#e0f2fe"),
            "canceled": ("#991b1b", "#fef2f2"),
            "expired": ("#374151", "#f3f4f6"),
        }
        fg, bg = colors.get(obj.status, ("#374151", "#f3f4f6"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:20px;'
            'font-weight:600;font-size:0.8rem;">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description="Session Window")
    def time_slot_display(self, obj):
        if obj.status == "postponed":
            return format_html(
                '<span style="color:#64748b;font-style:italic;">Hidden (postponed)</span>'
            )
        slot = obj.time_slot
        if slot == "Not Scheduled":
            return format_html('<span style="color:#94a3b8;">Not Scheduled</span>')
        return format_html('<strong style="color:#3b82f6;">{}</strong>', slot)

    @admin.display(description="Days Left")
    def days_left_display(self, obj):
        days = obj.days_left
        if obj.status == "postponed":
            return format_html(
                '<span style="color:#075985;">⏸ {} days (frozen)</span>', days
            )
        if obj.status == "active":
            color = "#166534" if days > 7 else "#dc2626"
            return format_html('<span style="color:{};">▶ {} days</span>', color, days)
        return format_html('<span style="color:#94a3b8;">—</span>')

    # ------------------------------------------------------------------
    # Enforce full_clean() on every admin save so clean() runs
    # ------------------------------------------------------------------

    def save_model(self, request, obj, form, change):
        try:
            obj.full_clean()
        except ValidationError as e:
            # Re-raise so Django admin shows the error inline
            from django.contrib.admin.utils import flatten_fieldsets
            from django.core.exceptions import ValidationError as VE
            raise VE(e.messages)
        super().save_model(request, obj, form, change)

    # ------------------------------------------------------------------
    # Status transition guard
    # ------------------------------------------------------------------

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None:
            status_field = form.base_fields.get("status")
            if status_field:
                current = obj.status
                # Define allowed transitions
                allowed = {
                    "pending": ["pending", "active", "canceled"],
                    "active": ["active", "postponed", "canceled", "expired"],
                    "postponed": ["postponed", "active", "canceled"],
                    "canceled": ["canceled"],
                    "expired": ["expired"],
                }
                valid_statuses = allowed.get(current, [s for s, _ in Membership.STATUS_CHOICES])
                status_field.choices = [
                    (value, label)
                    for value, label in Membership.STATUS_CHOICES
                    if value in valid_statuses
                ]
        return form


@admin.register(MembershipNote)
class MembershipNoteAdmin(admin.ModelAdmin):
    list_display = ("membership", "author", "short_content", "created_at")
    list_filter = ("author", "created_at")
    search_fields = ("content", "membership__user__username")
    readonly_fields = ("created_at",)

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:80] + ("…" if len(obj.content) > 80 else "")
