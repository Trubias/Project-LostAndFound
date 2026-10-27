from django.db import models
from django.contrib.auth.models import User
from config.validators import validate_image_upload


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


class ReportLocation(models.Model):
    CAMPUS = 'CAMPUS'
    BUILDING = 'BUILDING'
    ROOM = 'ROOM'
    KIND_CHOICES = [(CAMPUS, 'Campus'), (BUILDING, 'Building'), (ROOM, 'Room / Computer Lab')]
    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['kind', 'name']

    def __str__(self):
        return f'{self.get_kind_display()}: {self.name}'


class Item(models.Model):
    # Item type choices
    TYPE_LOST = 'LOST'
    TYPE_FOUND = 'FOUND'
    ITEM_TYPE_CHOICES = [
        (TYPE_LOST, 'Lost'),
        (TYPE_FOUND, 'Found'),
    ]

    # Status choices — lifecycle for Lost items:
    #   ACTIVE (Lost — not yet seen/found)
    #   UNCLAIMED (Seen/found by someone, waiting for owner to claim)
    #   CLAIMED  (Owner has claimed / returned)
    #   ARCHIVED (Admin-archived / resolved old records)
    STATUS_ACTIVE = 'ACTIVE'        # Lost: not yet seen
    STATUS_UNCLAIMED = 'UNCLAIMED'  # Seen/found — awaiting owner claim
    STATUS_CLAIMED = 'CLAIMED'      # Owner has claimed it
    STATUS_ARCHIVED = 'ARCHIVED'    # Archived / closed
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Lost'),       # display as "Lost" in UI
        (STATUS_UNCLAIMED, 'Unclaimed'),
        (STATUS_CLAIMED, 'Claimed'),
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
    contact_phone = models.CharField(max_length=32, blank=True)
    building = models.CharField(max_length=120, blank=True)
    room = models.CharField(max_length=80, blank=True)
    workstation = models.CharField(max_length=120, blank=True)
    date_occurred = models.DateField(help_text='Date the item was lost or found')
    approximate_time = models.TimeField(blank=True, null=True)
    image = models.ImageField(
        upload_to='item_images/', blank=True, null=True,
        validators=[validate_image_upload],
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reported_items'
    )
    found_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='found_items',
    )
    found_at = models.DateTimeField(null=True, blank=True)
    found_description = models.TextField(blank=True)
    found_image = models.ImageField(
        upload_to='item_images/found_evidence/', blank=True, null=True,
        validators=[validate_image_upload],
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
        """Active = status is ACTIVE (Lost — not yet seen)."""
        return self.status == self.STATUS_ACTIVE

    def is_unclaimed(self):
        """Unclaimed = item has been seen/found, waiting for owner."""
        return self.status == self.STATUS_UNCLAIMED

    def is_claimed(self):
        """Claimed = owner has retrieved the item."""
        return self.status == self.STATUS_CLAIMED

    def is_archived(self):
        return self.status == self.STATUS_ARCHIVED

    def get_status_display_label(self):
        """Human-readable status label for templates."""
        mapping = {
            self.STATUS_ACTIVE: 'Found' if self.is_found() else 'Lost',
            self.STATUS_UNCLAIMED: 'Unclaimed',
            self.STATUS_CLAIMED: 'Claimed',
            self.STATUS_ARCHIVED: 'Archived',
        }
        return mapping.get(self.status, self.status)

    def get_status_display(self):
        return self.get_status_display_label()

    def get_status_badge_class(self):
        """Bootstrap badge color class for each status."""
        if self.status == self.STATUS_ACTIVE and self.is_found():
            return 'success'
        mapping = {
            self.STATUS_ACTIVE: 'warning',      # Lost → orange
            self.STATUS_UNCLAIMED: 'info',       # Unclaimed → blue
            self.STATUS_CLAIMED: 'success',      # Claimed → green
            self.STATUS_ARCHIVED: 'secondary',   # Archived → gray
        }
        return mapping.get(self.status, 'secondary')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
