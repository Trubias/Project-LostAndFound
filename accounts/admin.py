from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('role', 'phone', 'profile_image', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'profile__role')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Admins can only see their own account
        return qs.filter(pk=request.user.pk)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.pk != request.user.pk:
            return False
        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if obj is not None and obj.pk != request.user.pk:
            return False
        return super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.pk != request.user.pk:
            return False
        return super().has_delete_permission(request, obj)

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except Profile.DoesNotExist:
            return '—'
    get_role.short_description = 'Role'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_full_name', 'role', 'phone', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Admins can only see their own profile
        return qs.filter(user=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.user != request.user:
            return False
        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if obj is not None and obj.user != request.user:
            return False
        return super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.user != request.user:
            return False
        return super().has_delete_permission(request, obj)

    def get_full_name(self, obj):
        return obj.user.get_full_name() or '—'
    get_full_name.short_description = 'Full Name'


# Re-register UserAdmin with Profile inline
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
