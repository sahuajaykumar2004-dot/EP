from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CollegeProfile, Course, Event, Gallery,
    Faculty, Hostel
)


# ============================================
# 🔵 INLINE MODELS
# ============================================

class CourseInline(admin.TabularInline):
    model = Course
    extra = 1


class FacultyInline(admin.TabularInline):
    model = Faculty
    extra = 1


class GalleryInline(admin.TabularInline):
    model = Gallery
    extra = 1


class HostelInline(admin.TabularInline):
    model = Hostel
    extra = 1


# ============================================
# 🔵 COLLEGE PROFILE ADMIN
# ============================================

@admin.register(CollegeProfile)
class CollegeProfileAdmin(admin.ModelAdmin):
    list_display = (
        "college_name",
        "college_code",
        "college_type",
        "state",
        "verified",
        "is_popular",
        "is_featured",
    )
    search_fields = ("college_name", "college_code", "email", "phone")
    list_filter = ("college_type", "state", "verified", "is_popular", "is_featured")
    readonly_fields = ("created_at", "updated_at", "logo_preview", "image_preview")

    inlines = [CourseInline, FacultyInline, GalleryInline, HostelInline]

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "user",
                "college_name",
                "college_code",
                "official_registration_no",
                "college_type",
                "established_year",
                "accreditation_body",
            )
        }),
        ("Contact & Location", {
            "fields": (
                "country",
                "state",
                "district",
                "pin_code",
                "address",
                "email",
                "phone",
                "landline",
                "website",
                "contact_person",
            )
        }),
        ("Media", {
            "fields": (
                "college_logo", "logo_preview",
                "college_image", "image_preview",
                "credential_image",
            )
        }),
        ("Status", {
            "fields": (
                "verified",
                "approved_by",
                "approved_at",
                "is_popular",
                "is_featured",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def logo_preview(self, obj):
        if obj.college_logo:
            return format_html(f"<img src='{obj.college_logo.url}' width='120' height='120' />")
        return "No Logo"
    logo_preview.short_description = "Logo Preview"

    def image_preview(self, obj):
        if obj.college_image:
            return format_html(f"<img src='{obj.college_image.url}' width='200' />")
        return "No Image"
    image_preview.short_description = "Main Image Preview"


# ============================================
# 🔵 COURSE ADMIN
# ============================================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "degree",
        "specialization",
        "college",
        "level",
        "duration",
        "fee",
    )
    search_fields = ("degree", "specialization", "college__college_name")
    list_filter = ("level", "main_stream")
    ordering = ("college", "degree")


# ============================================
# 🔵 EVENT ADMIN
# ============================================

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "college", "date", "location")
    search_fields = ("name", "college__college_name")
    list_filter = ("date",)

    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(f"<img src='{obj.image.url}' width='200' />")
        return "No Image"
    image_preview.short_description = "Event Image Preview"


# ============================================
# 🔵 GALLERY ADMIN
# ============================================

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ("college", "media_type", "title", "display_order")
    list_filter = ("media_type",)
    search_fields = ("title", "college__college_name")

    readonly_fields = ("media_preview",)

    def media_preview(self, obj):
        if obj.file:
            if obj.media_type == "image":
                return format_html(f"<img src='{obj.file.url}' width='200' />")
            return format_html(f"<video src='{obj.file.url}' width='220' controls></video>")
        return "No Media"


# ============================================
# 🔵 FACULTY ADMIN
# ============================================

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "designation", "department", "college", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("name", "designation", "college__college_name")

    readonly_fields = ("photo_preview",)

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(f"<img src='{obj.photo.url}' width='150' />")
        return "No Photo"


# ============================================
# 🔵 HOSTEL ADMIN
# ============================================

@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ("name", "college", "type", "fee", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("name", "college__college_name")

    readonly_fields = ("images_preview",)

    def images_preview(self, obj):
        if obj.images:
            previews = "".join(
                f"<img src='{img}' width='120' style='margin-right:5px;border-radius:6px;' />"
                for img in obj.images
            )
            return format_html(previews)
        return "No Images"
