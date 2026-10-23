from django import forms
from django.utils import timezone
from .models import Claim


class ClaimForm(forms.ModelForm):
    """
    Form for submitting a claim. Only message and proof_description are user-editable.
    claimant, item, status, reviewed_by, and reviewed_at are set server-side.
    """

    class Meta:
        model = Claim
        fields = ['message', 'proof_description']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': (
                    'Explain why you believe this item belongs to you. '
                    'For example: "I lost this on Monday near the library. '
                    'It has my name written inside."'
                ),
            }),
            'proof_description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': (
                    'Describe unique identifying marks, contents, serial numbers, '
                    'colour, size, or any other detail that proves ownership. '
                    'The more specific, the better.'
                ),
            }),
        }
        labels = {
            'message': 'Why do you believe this item belongs to you?',
            'proof_description': 'Proof of Ownership / Identifying Details',
        }
        help_texts = {
            'message': 'Tell us your story. Be specific about when and where you lost the item.',
            'proof_description': (
                'Provide unique marks, contents, serial numbers, or other identifying '
                'information that only the true owner would know.'
            ),
        }

    def clean_message(self):
        msg = self.cleaned_data.get('message', '').strip()
        if len(msg) < 20:
            raise forms.ValidationError(
                'Please provide a more detailed message (at least 20 characters).'
            )
        return msg

    def clean_proof_description(self):
        proof = self.cleaned_data.get('proof_description', '').strip()
        if len(proof) < 20:
            raise forms.ValidationError(
                'Please provide more specific identifying details (at least 20 characters).'
            )
        return proof


class ReviewClaimForm(forms.Form):
    """Form for reviewers (item reporter or admin) to approve/reject a claim."""
    reviewer_notes = forms.CharField(
        label='Reviewer Notes',
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Add notes about your decision (optional but recommended).',
        }),
        required=False,
    )


class HandoffScheduleForm(forms.Form):
    handoff_location = forms.CharField(
        label='Pickup location', max_length=240,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Public campus location, e.g. Library front desk'}),
    )
    handoff_at = forms.DateTimeField(
        label='Date and time',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
    )
    handoff_instructions = forms.CharField(
        label='Instructions', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional meeting instructions'}),
    )

    def clean_handoff_at(self):
        value = self.cleaned_data['handoff_at']
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        if value <= timezone.now():
            raise forms.ValidationError('Choose a future date and time.')
        return value


class HandoffResponseForm(forms.Form):
    action = forms.ChoiceField(choices=[('confirm', 'Confirm this pickup plan'), ('request_change', 'Request a different time or place')])
    handoff_change_request = forms.CharField(
        label='Suggested change', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Suggest another time or public meeting place'}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('action') == 'request_change' and len(cleaned.get('handoff_change_request', '').strip()) < 5:
            self.add_error('handoff_change_request', 'Describe the time or place you would like to change.')
        return cleaned
    action = forms.ChoiceField(
        label='Decision',
        choices=[
            ('approve', 'Approve — confirm ownership and resolve item'),
            ('reject', 'Reject — deny this claim'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
