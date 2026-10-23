from django import forms
from .models import Item, Category, ReportLocation
from .locations import BUILDING_CHOICES, LOCATION_CHOICES, ROOM_CHOICES


class ItemForm(forms.ModelForm):
    """Form for reporting a Lost or Found item. Reporter is set in the view."""

    class Meta:
        model = Item
        fields = [
            'title', 'description', 'category', 'location', 'building', 'room',
            'workstation', 'date_occurred', 'approximate_time', 'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Black Samsung Galaxy S22',
                'id': 'id_title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the item in detail (color, brand, markings, etc.)',
                'id': 'id_description',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Library 2nd Floor, Room 301, Cafeteria',
                'id': 'id_location',
            }),
            'building': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Building'}),
            'room': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ComLab 2'}),
            'workstation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PC 14 or near the printer'}),
            'date_occurred': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_date_occurred',
            }),
            'approximate_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'id_image',
            }),
        }
        labels = {
            'title': 'Item Name / Title',
            'description': 'Description',
            'category': 'Category',
            'location': 'Location',
            'building': 'Building (optional)',
            'room': 'Room / Computer Lab (optional)',
            'workstation': 'Workstation / Landmark (optional)',
            'date_occurred': 'Date Lost/Found',
            'approximate_time': 'Approximate Time (optional)',
            'image': 'Upload Image (optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def choices_with_existing(kind, fallback, value):
            configured = list(ReportLocation.objects.filter(kind=kind, active=True).order_by('name').values_list('name', 'name'))
            choices = configured or fallback
            if value and value not in {choice[0] for choice in choices}:
                return [*choices, (value, value)]
            return choices

        self.fields['location'] = forms.ChoiceField(
            choices=[('', 'Select a campus'), *choices_with_existing(ReportLocation.CAMPUS, LOCATION_CHOICES, self.instance.location)],
            required=True,
            widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_location'}),
        )
        self.fields['building'] = forms.ChoiceField(
            choices=[('', 'Select a building'), *choices_with_existing(ReportLocation.BUILDING, BUILDING_CHOICES, self.instance.building)],
            required=False,
            widget=forms.Select(attrs={'class': 'form-select'}),
        )
        self.fields['room'] = forms.ChoiceField(
            choices=[('', 'Select a room or computer lab'), *choices_with_existing(ReportLocation.ROOM, ROOM_CHOICES, self.instance.room)],
            required=False,
            widget=forms.Select(attrs={'class': 'form-select'}),
        )
        self.fields['category'].empty_label = '— Select Category —'
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['date_occurred'].required = True
        self.fields['title'].required = True
        self.fields['description'].required = True
        self.fields['location'].required = True

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 3:
            raise forms.ValidationError('Title must be at least 3 characters.')
        return title

    def clean_description(self):
        desc = self.cleaned_data.get('description', '').strip()
        if len(desc) < 10:
            raise forms.ValidationError('Description must be at least 10 characters.')
        return desc

    def clean_location(self):
        location = self.cleaned_data.get('location', '').strip()
        if len(location) < 3:
            raise forms.ValidationError('Location must be at least 3 characters.')
        return location


class CategoryForm(forms.ModelForm):
    """Form for Admins to create and edit Categories."""

    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Electronics, Bags, Books...',
                'id': 'id_category_name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Short description of the category (optional)',
                'id': 'id_category_description',
            }),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description (optional)',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Category name must be at least 2 characters.')
        # Check uniqueness case-insensitively
        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'Category "{name}" already exists.')
        return name


class ReportLocationForm(forms.ModelForm):
    class Meta:
        model = ReportLocation
        fields = ['name', 'kind', 'active']

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        duplicate = ReportLocation.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError('A location with this name already exists.')
        return name

