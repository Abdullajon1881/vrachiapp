from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile, Region, City, District, DoctorApplication, Consultation, Message, AIDialogue, AIMessage


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_staff', 'is_verified', 'google_id']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'is_verified', 'date_joined']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'avatar', 'google_id', 'is_verified')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'avatar', 'google_id', 'is_verified')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'gender', 'date_of_birth', 'emergency_contact']
    list_filter = ['gender', 'date_of_birth']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'type']
    list_filter = ['type']
    search_fields = ['name']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'region']
    list_filter = ['region']
    search_fields = ['name', 'region__name']
    raw_id_fields = ['region']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'city']
    list_filter = ['region', 'city']
    search_fields = ['name', 'region__name', 'city__name']
    raw_id_fields = ['region', 'city']


@admin.register(DoctorApplication)
class DoctorApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'status', 'created_at']
    list_filter = ['status', 'specialization', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'specialization']
    raw_id_fields = ['user']


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'doctor', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['patient__email', 'doctor__email']
    raw_id_fields = ['patient', 'doctor']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'sender', 'content_preview', 'created_at', 'is_read')
    list_filter = ('created_at', 'is_read')
    search_fields = ('content', 'sender__email')
    raw_id_fields = ('consultation', 'sender')
    readonly_fields = ('created_at', 'read_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Содержание'


@admin.register(AIDialogue)
class AIDialogueAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at', 'updated_at', 'is_active')
    list_filter = ('created_at', 'updated_at', 'is_active')
    search_fields = ('title', 'user__email', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'dialogue', 'sender_type', 'message_type', 'content_preview', 'timestamp')
    list_filter = ('sender_type', 'message_type', 'timestamp')
    search_fields = ('content', 'dialogue__title')
    raw_id_fields = ('dialogue',)
    readonly_fields = ('timestamp',)
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Содержание' 