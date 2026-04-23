from django import forms
from .models import TrainingPlan

class MembershipContactForm(forms.Form):
    # This form is now used for the initial Application/Request
    plan = forms.ModelChoiceField(
        queryset=TrainingPlan.objects.all(),
        widget=forms.HiddenInput()
    )
    goals = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "What are your specific performance goals?"}),
        required=True,
        label="Training Goals"
    )
    preferred_times = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Mon/Wed/Fri mornings"}),
        required=False,
        label="Preferred Availability"
    )
