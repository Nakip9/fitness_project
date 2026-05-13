from django.contrib import admin

from .models import Payment, PaymentRequest


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "amount", "status", "created_at")
    list_filter = ("status", "plan")
    search_fields = ("user__username", "plan__name", "stripe_payment_intent")


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "plan", "user", "status", "created_at")
    list_filter = ("status", "plan")
    search_fields = ("phone_number", "plan__name", "user__username")
    actions = ["approve_and_create_payment"]

    @admin.action(description="Approve and Create Payment")
    def approve_and_create_payment(self, request, queryset):
        from .models import Payment
        from memberships.models import Membership
        from django.contrib import messages
        
        count = 0
        for req in queryset:
            if req.status == 'pending':
                # Find or create membership
                membership = Membership.objects.filter(
                    user=req.user, 
                    plan=req.plan, 
                    status='pending'
                ).first()
                
                if not membership:
                    membership = Membership.objects.create(
                        user=req.user,
                        plan=req.plan,
                        status='pending'
                    )
                
                # Create Payment
                Payment.objects.create(
                    user=req.user,
                    plan=req.plan,
                    membership=membership,
                    amount=req.plan.price,
                    status='created'
                )
                req.status = 'contacted'
                req.save()
                count += 1
        
        self.message_user(request, f"{count} payment requests approved and payments created.", messages.SUCCESS)
