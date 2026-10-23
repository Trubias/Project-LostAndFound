from django.contrib import admin
from .models import Claim


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'item', 'claimant', 'status', 'reviewed_by', 'created_at', 'reviewed_at'
    ]
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = [
        'item__title',
        'claimant__username',
        'claimant__email',
        'message',
        'proof_description',
    ]
    readonly_fields = [field.name for field in Claim._meta.fields]
    ordering = ['-created_at']
    list_per_page = 25

    fieldsets = (
        ('Claim Info', {
            'fields': ('item', 'claimant', 'message', 'proof_description')
        }),
        ('Status & Review', {
            'fields': ('status', 'reviewed_by', 'reviewer_notes', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
