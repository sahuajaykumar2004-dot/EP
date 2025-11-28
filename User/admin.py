from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import (
    User, EmailOTP, PhoneOTP,
    PreRegistration, PreEmailOTP, PrePhoneOTP
)


# =====================================================
# 🔹 INLINE OTPS FOR USER
# =====================================================

class EmailOTPInline(admin.TabularInline):
    model = EmailOTP
    extra = 0
    readonly_fields = ("otp", "created_at", "verified")


class PhoneOTPInline(admin.TabularInline):
    model = PhoneOTP
    extra = 0
    readonly_fields = ("otp", "created_at", "verified")


# =====================================================
# 🔹 CUSTOM USER ADMIN
# =====================================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "email", "name", "user_type",
        "email_verified", "phone_verified", "verified",
        "is_profile_complete", "is_active"
    )
    list_filter = ("user_type", "verified", "email_verified", "phone_verified", "is_active")
    search_fields = ("email", "name", "phone")

    ordering = ("email",)

    readonly_fields = (
        "last_login",
        "date_joined",
        "email_verified",
        "phone_verified",
        "verified",
        "is_profile_complete",
    )

    fieldsets = (
        ("Login Credentials", {
            "fields": ("email", "password")
        }),
        ("Personal Info", {
            "fields": ("name", "phone", "user_type")
        }),
        ("Verification Status", {
            "fields": (
                "email_verified",
                "phone_verified",
                "verified",
                "is_profile_complete",
            )
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important Dates", {
            "fields": ("last_login", "date_joined")
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "user_type")
        }),
    )

    inlines = [EmailOTPInline, PhoneOTPInline]


# =====================================================
# 🔹 EMAIL OTP ADMIN
# =====================================================

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "verified")
    search_fields = ("user__email", "otp")
    list_filter = ("verified",)

    readonly_fields = ("otp", "created_at")


# =====================================================
# 🔹 PHONE OTP ADMIN
# =====================================================

@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "verified")
    search_fields = ("user__email", "otp")
    list_filter = ("verified",)

    readonly_fields = ("otp", "created_at")


# =====================================================
# 🔹 INLINE OTPS FOR PREREGISTRATION
# =====================================================

class PreEmailOTPInline(admin.TabularInline):
    model = PreEmailOTP
    extra = 0
    readonly_fields = ("otp", "created_at", "verified")


class PrePhoneOTPInline(admin.TabularInline):
    model = PrePhoneOTP
    extra = 0
    readonly_fields = ("otp", "created_at", "verified")


# =====================================================
# 🔹 PREREGISTRATION ADMIN
# =====================================================

@admin.register(PreRegistration)
class PreRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "email", "phone", "user_type",
        "email_verified", "phone_verified",
        "token", "created_at"
    )
    list_filter = ("email_verified", "phone_verified", "user_type")
    search_fields = ("email", "phone", "token")

    readonly_fields = ("token", "password_hash", "created_at")

    inlines = [PreEmailOTPInline, PrePhoneOTPInline]


# =====================================================
# 🔹 PREREG EMAIL OTP ADMIN
# =====================================================

@admin.register(PreEmailOTP)
class PreEmailOTPAdmin(admin.ModelAdmin):
    list_display = ("pre", "otp", "created_at", "verified")
    search_fields = ("pre__email", "otp")
    readonly_fields = ("otp", "created_at")


# =====================================================
# 🔹 PREREG PHONE OTP ADMIN
# =====================================================

@admin.register(PrePhoneOTP)
class PrePhoneOTPAdmin(admin.ModelAdmin):
    list_display = ("pre", "otp", "created_at", "verified")
    search_fields = ("pre__email", "otp")
    readonly_fields = ("otp", "created_at")


admin.site.site_header = "Education Pioneer Admin "  # Top header
admin.site.site_title = " Education Pioneer Admin "   # Browser tab title
admin.site.index_title = "Dashboard"  
    

