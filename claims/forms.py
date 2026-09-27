from django import forms
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
    action = forms.ChoiceField(
        label='Decision',
        choices=[
            ('approve', 'Approve — confirm ownership and resolve item'),
            ('reject', 'Reject — deny this claim'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
