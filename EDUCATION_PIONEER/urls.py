from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from User.views import admin_logout_redirect

urlpatterns = [
    # Place the custom admin logout route BEFORE the admin.site.urls include
    # so it overrides the default Django admin logout URL.
    path('admin/logout/', admin_logout_redirect, name='admin-logout'),
    path('admin/', admin.site.urls),

    # ==========================
    # API Routes
    # ==========================
    path('api/users/', include('User.urls')),
    path('api/students/', include('Student.urls')),
    path('api/consultants/', include('Consultant.urls')),
    path('api/colleges/', include('College.urls')),
]

# ==========================
# Serve Media Files (only in DEBUG)
# ==========================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
