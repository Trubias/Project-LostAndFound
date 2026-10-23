from django.contrib import admin

from .models import AbuseReport


@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'submitted_by', 'reason', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('item__title', 'submitted_by__username', 'details', 'reviewer_notes')
    readonly_fields = ('item', 'submitted_by', 'reason', 'details', 'created_at', 'updated_at')
    list_select_related = ('item', 'submitted_by', 'reviewed_by')
    list_per_page = 50
