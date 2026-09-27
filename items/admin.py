from django.contrib import admin
from .models import Category, Item


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type', 'category', 'location', 'status', 'reporter', 'date_occurred', 'created_at')
    list_filter = ('item_type', 'category', 'status', 'date_occurred', 'created_at')
    search_fields = ('title', 'description', 'location', 'reporter__username', 'reporter__email', 'category__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Item Information', {
            'fields': ('title', 'description', 'item_type', 'category', 'location', 'date_occurred', 'image')
        }),
        ('Status & Reporter', {
            'fields': ('status', 'reporter', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Staff and superusers can see all items in admin
        return qs

    actions = ['archive_items', 'restore_items']


    @admin.action(description='Archive selected items')
    def archive_items(self, request, queryset):
        queryset.update(status=Item.STATUS_ARCHIVED)
        self.message_user(request, f'{queryset.count()} item(s) archived.')

    @admin.action(description='Restore selected items')
    def restore_items(self, request, queryset):
        queryset.update(status=Item.STATUS_ACTIVE)
        self.message_user(request, f'{queryset.count()} item(s) restored.')
