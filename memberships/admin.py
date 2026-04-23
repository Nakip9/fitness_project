from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import TrainingPlan, Membership, MembershipNote, AuditLog

@admin.register(TrainingPlan)
class TrainingPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price_display", "duration_days")
    
    def price_display(self, obj):
        return f"${obj.price_cents / 100:.2f}"
    price_display.short_description = "Price"

class MembershipNoteInline(admin.TabularInline):
    model = MembershipNote
    extra = 1
    fields = ("author", "content", "is_pinned")

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("trainee", "coach", "status", "payment_status", "scheduled_start")
    list_filter = ("status", "payment_status", "coach")
    search_fields = ("trainee__username", "trainee__email")
    inlines = [MembershipNoteInline]
    
    actions = ["approve_membership", "mark_as_paid"]

    fieldsets = (
        ("Participants", {
            "fields": ("trainee", "coach", "plan")
        }),
        ("Status & Workflow", {
            "fields": ("status", "payment_status")
        }),
        ("Schedule (UTC)", {
            "fields": ("scheduled_start", "scheduled_end")
        }),
    )

    def approve_membership(self, request, queryset):
        """Requirement 6: Trigger Approval & Email."""
        for membership in queryset.filter(status=Membership.Status.REQUESTED):
            membership.status = Membership.Status.APPROVED
            membership.save()
            
            # Automated Email
            subject = f"Your Training with {getattr(settings, 'SITE_NAME', 'JafriFit')} is APPROVED!"
            message = (
                f"Hello {membership.trainee.username},\n\n"
                f"Your request for the '{membership.plan.name}' has been approved by the coach.\n\n"
                f"SCHEDULE:\n"
                f"Start: {membership.scheduled_start}\n"
                f"Duration: {membership.plan.duration_days} Days\n\n"
                f"PAYMENT STATUS: {membership.get_payment_status_display()}\n\n"
                f"Please log in to your dashboard to complete the next steps."
            )
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@jafrifit.com'),
                [membership.trainee.email],
                fail_silently=True,
            )
            
            AuditLog.objects.create(
                membership=membership,
                actor=request.user,
                action="ADMIN_APPROVAL",
                new_state={"status": "APPROVED"}
            )
            
        self.message_user(request, "Selected requests approved and notification emails sent.")
    
    def mark_as_paid(self, request, queryset):
        for membership in queryset:
            membership.payment_status = Membership.PaymentStatus.PAID
            membership.status = Membership.Status.ACTIVE
            membership.save()
            
            AuditLog.objects.create(
                membership=membership,
                actor=request.user,
                action="MANUAL_PAYMENT_VERIFIED",
                new_state={"payment_status": "PAID", "status": "ACTIVE"}
            )
    mark_as_paid.short_description = "Verify Payment & Activate Coaching"

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("membership", "actor", "action", "timestamp")
    readonly_fields = ("membership", "actor", "action", "old_state", "new_state", "timestamp")
