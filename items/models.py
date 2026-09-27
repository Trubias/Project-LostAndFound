from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']


class Item(models.Model):
    # Item type choices
    TYPE_LOST = 'LOST'
    TYPE_FOUND = 'FOUND'
    ITEM_TYPE_CHOICES = [
        (TYPE_LOST, 'Lost'),
        (TYPE_FOUND, 'Found'),
    ]

    # Status choices
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_ARCHIVED = 'ARCHIVED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )
    location = models.CharField(max_length=200)
    date_occurred = models.DateField(help_text='Date the item was lost or found')
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reported_items'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_item_type_display()}] {self.title}"

    def is_lost(self):
        return self.item_type == self.TYPE_LOST

    def is_found(self):
        return self.item_type == self.TYPE_FOUND

    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    def is_archived(self):
        return self.status == self.STATUS_ARCHIVED

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
