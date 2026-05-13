from django import forms

from .models import MembershipPlan


class MembershipContactForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=MembershipPlan.objects.none(),
        widget=forms.RadioSelect(attrs={"class": "d-none"}),
        empty_label=None,
    )
    phone_number = forms.CharField(
        max_length=32,
        label="Phone number",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "e.g. +1 555 123 4567",
                "autocomplete": "tel",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        plans = kwargs.pop("plans", None)
        initial_plan = kwargs.pop("initial_plan", None)
        super().__init__(*args, **kwargs)
        if plans is None:
            plans = MembershipPlan.objects.filter(is_active=True)
        self.fields["plan"].queryset = plans
        if initial_plan is not None:
            self.initial.setdefault("plan", initial_plan)
