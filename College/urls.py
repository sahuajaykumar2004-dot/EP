from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (CollegeProfileView, CollegeListView, CourseViewSet, EventViewSet, 
                    GalleryViewSet, FacultyViewSet, HostelImageUploadView,HostelListCreateView,
                    HostelDetailView, FilterOptionsAPIView)

# 🔹 DRF router for viewsets (Courses)
router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'events', EventViewSet, basename='event')
router.register(r'gallery', GalleryViewSet, basename='gallery')
router.register("faculties", FacultyViewSet, basename="faculties")

urlpatterns = [
    # 🔹 College list endpoint (with comprehensive filtering)
    path("list/", CollegeListView.as_view(), name="college-list"),
    path("filters/", FilterOptionsAPIView.as_view(), name="filter-options"),
    path("filters/<str:filter_name>/", FilterOptionsAPIView.as_view(), name="single-filter"),
    
    # 🔹 College profile endpoint
    path("profile/", CollegeProfileView.as_view(), name="college-profile"),
    path("hostels/", HostelListCreateView.as_view(), name="hostels"),
    path("hostels/<int:pk>/", HostelDetailView.as_view(), name="hostel-detail"),
    path("hostels/upload-image/", HostelImageUploadView.as_view(), name="hostel-image-upload"),

    # 🔹 Include all course-related endpoints
    path("", include(router.urls)),
]
