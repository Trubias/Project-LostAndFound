from django import forms
from .models import Item, Category


class ItemForm(forms.ModelForm):
    """Form for reporting a Lost or Found item. Reporter is set in the view."""

    class Meta:
        model = Item
        fields = ['title', 'description', 'category', 'location', 'date_occurred', 'image']
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
            'date_occurred': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_date_occurred',
            }),
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
            'date_occurred': 'Date Lost/Found',
            'image': 'Upload Image (optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

