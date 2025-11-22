from rest_framework import generics, viewsets,permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Course, CollegeProfile,Event,Gallery,Faculty,Hostel
from .serializers import CollegeProfileSerializer,CourseSerializer,EventSerializer,GallerySerializer,FacultySerializer,HostelSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from College import serializers
from django_filters.rest_framework import DjangoFilterBackend




class CollegeProfileView(generics.RetrieveUpdateAPIView):
    """
    College Profile Setup & Update View
    - GET → Retrieve current college profile
    - PUT/PATCH → Update profile (both initial setup or later edits)
    """

    serializer_class = CollegeProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        """Return the logged-in college user's profile."""
        user = self.request.user
        if user.user_type != "college":
            return Response(
                {"detail": "Only college users can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        profile, _ = CollegeProfile.objects.get_or_create(
            user=user,
            defaults={
                "college_name": user.name or f"College_{user.id}",
                "email": user.email,
                "phone": user.phone,
                "country": "",
                "state": "",
                "district": "",
                "address": "",
            },
        )
        return profile

    def get(self, request, *args, **kwargs):
        """Retrieve profile data."""
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        """Full update (used when saving setup form)."""
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Profile updated successfully."}
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        """Partial update (used for dashboard edit)."""
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Profile updated successfully."}
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CollegeListView(generics.ListAPIView):
    """
    List and filter colleges with comprehensive filtering options.
    
    Colleges are automatically categorized by the main_stream of courses they offer.
    A college offering engineering AND medical courses will appear when filtering 
    by either 'engineering' OR 'medical'.
    
    Supported Filters:
    - country: Filter by country (case-insensitive substring match)
    - state: Filter by state (case-insensitive substring match)
    - district: Filter by district (case-insensitive substring match)
    - main_stream: Filter colleges by courses' main stream (engineering, law, finance, medical, arts)
      (e.g., ?main_stream=engineering returns all colleges offering engineering courses)
    - college_type: Filter by college type (government, private, autonomous)
    - verified: Filter by verification status (true/false)
    - is_popular: Filter by popular status (true/false)
    - is_featured: Filter by featured status (true/false)
    
    Example queries:
    - /api/colleges/list/?country=India&state=California
    - /api/colleges/list/?main_stream=engineering&college_type=private
    - /api/colleges/list/?state=Tamil+Nadu&verified=true
    - /api/colleges/list/?district=Chennai&main_stream=medical
    - /api/colleges/list/?main_stream=arts&is_popular=true
    """
    serializer_class = CollegeProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Define filterable fields
    filterset_fields = {
        'country': ['icontains'],
        'state': ['icontains'],
        'district': ['icontains'],
        'college_type': ['exact'],
        'verified': ['exact'],
        'is_popular': ['exact'],
        'is_featured': ['exact'],
    }
    
    # Search fields
    search_fields = ['college_name', 'country', 'state', 'district', 'about_college']
    
    # Ordering fields
    ordering_fields = ['college_name', 'created_at', 'is_popular', 'is_featured']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter colleges dynamically, including by courses' main_stream.
        """
        queryset = CollegeProfile.objects.distinct()
        
        # Handle main_stream filter (filter by related courses' main_stream)
        main_stream = self.request.query_params.get('main_stream')
        if main_stream:
            queryset = queryset.filter(courses__main_stream=main_stream).distinct()
        
        return queryset


class CourseViewSet(viewsets.ModelViewSet):
    """
    Manage all courses (CRUD)
    
    Supported Filters:
    - level: Filter by course level (undergraduate, postgraduate)
    - degree: Filter by degree type (btech, mtech, ba, llb, mba, mbbs)
    - main_stream: Filter by main stream (engineering, law, finance, medical, arts)
    - specialization: Filter by specialization (case-insensitive substring match)
    - college__college_code: Filter by college code
    - college__country: Filter by college country
    - college__state: Filter by college state
    - college__district: Filter by college district
    - fee__lte: Filter courses with fee less than or equal to value
    - fee__gte: Filter courses with fee greater than or equal to value
    
    Example queries:
    - /api/courses/?level=undergraduate&main_stream=engineering
    - /api/courses/?degree=btech&college__state=California
    - /api/courses/?specialization=computer&fee__lte=100000
    - /api/courses/?college__country=India&main_stream=medical
    """
    serializer_class = CourseSerializer
    queryset = Course.objects.all().select_related('college')
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Define filterable fields
    filterset_fields = {
        'level': ['exact'],
        'degree': ['exact'],
        'main_stream': ['exact'],
        'specialization': ['icontains'],
        'college__college_code': ['exact'],
        'college__country': ['icontains'],
        'college__state': ['icontains'],
        'college__district': ['icontains'],
        'fee': ['lte', 'gte'],
    }
    
    # Search fields
    search_fields = ['specialization', 'college__college_name', 'description']
    
    # Ordering fields
    ordering_fields = ['created_at', 'fee', 'duration', 'degree']
    ordering = ['-created_at']

    def create(self, request, *args, **kwargs):
        """
        Create course using college_code instead of numeric ID
        """
        college_code = request.data.get('college')

        college = None
        # If college code is provided, use it
        if college_code:
            try:
                college = CollegeProfile.objects.get(college_code=college_code)
            except CollegeProfile.DoesNotExist:
                return Response({'error': 'Invalid college code.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # If no college code provided, try to infer from authenticated college user
            user = request.user
            if user and user.is_authenticated and getattr(user, 'user_type', None) == 'college':
                # get or create profile for user
                college, _ = CollegeProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'college_name': user.name or f"College_{user.id}",
                        'email': user.email,
                        'phone': user.phone,
                    },
                )
            else:
                return Response({'error': 'College code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(college=college)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='by-college/(?P<college_code>[^/.]+)')
    def by_college(self, request, college_code=None):
        """
        Custom endpoint: Get all courses for a specific college
        Example: /api/courses/by-college/C40B2C92D3/
        """
        college = get_object_or_404(CollegeProfile, college_code=college_code)
        courses = self.get_queryset().filter(college=college)
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

# -----------------------------

class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        college = getattr(user, "college_profile", None)
        queryset = Event.objects.all()

        # 🟢 Allow filtering by ?college=<id> or ?college=<code>
        college_param = self.request.query_params.get("college")
        if college_param:
            if college_param.isdigit():
                queryset = queryset.filter(college_id=college_param)  # if numeric -> use ID
            else:
                queryset = queryset.filter(college__code=college_param)  # if not numeric -> use code
        elif college:
            queryset = queryset.filter(college=college)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        college = serializer.validated_data.get("college")
        if not college:
            user_college = getattr(self.request.user, "college_profile", None)
            if user_college:
                serializer.save(college=user_college)
            else:
                raise serializers.ValidationError({"college": "College information missing."})
        else:
            serializer.save()

class GalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user_college = getattr(self.request.user, "college_profile", None)

        college_param = self.request.query_params.get("college")

        if college_param:
            if college_param.isdigit():
                return Gallery.objects.filter(college_id=college_param)
            return Gallery.objects.filter(college__code=college_param)

        if user_college:
            return Gallery.objects.filter(college=user_college)

        return Gallery.objects.none()

    def create(self, request, *args, **kwargs):
        files = (
            request.FILES.getlist("files")
            or request.FILES.getlist("file")
            or []
        )

        # single file fallback
        if not files and "file" in request.FILES:
            files = [request.FILES["file"]]

        if not files:
            return Response({"detail": "No files uploaded."}, status=400)

        media_type = request.data.get("media_type", "image")
        title = request.data.get("title", "")
        description = request.data.get("description", "")

        # use logged-in user's college
        user_college = getattr(request.user, "college_profile", None)

        if not user_college:
            return Response({"detail": "User is not associated with any college."}, status=400)

        created_items = []

        for file in files:
            serializer = self.get_serializer(data={
                "media_type": media_type,
                "file": file,
                "title": title,
                "description": description
            })

            # VALIDATE WITHOUT college (we add it later)
            serializer.is_valid(raise_exception=True)

            # NOW save with college
            item = serializer.save(college=user_college)

            created_items.append(self.get_serializer(item).data)

        return Response(created_items, status=status.HTTP_201_CREATED)


class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user_college = getattr(self.request.user, "college_profile", None)

        queryset = Faculty.objects.all()
        if user_college:
            queryset = queryset.filter(college=user_college)

        return queryset.order_by("display_order", "name")

    def create(self, request, *args, **kwargs):
        user_college = getattr(request.user, "college_profile", None)

        if not user_college:
            return Response(
                {"detail": "No college linked to this user."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(college=user_college)   # 🔥 AUTO-SET COLLEGE HERE

        return Response(serializer.data, status=status.HTTP_201_CREATED)

class HostelListCreateView(generics.ListCreateAPIView):
    serializer_class = HostelSerializer

    def get_queryset(self):
        college_id = self.request.query_params.get("college")
        if college_id:
            return Hostel.objects.filter(college=college_id)
        return Hostel.objects.none()  # no random list

class HostelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hostel.objects.all().order_by("id")
    serializer_class = HostelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class HostelImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # 🔹 Check image
        if "image" not in request.FILES:
            return Response({"error": "No image provided"}, status=400)

        image = request.FILES["image"]

        # 🔹 College ID
        college_id = request.data.get("college")
        if not college_id:
            return Response({"error": "College ID not provided"}, status=400)

        # 🔹 Check college exists
        try:
            college = CollegeProfile.objects.get(id=college_id)
        except CollegeProfile.DoesNotExist:
            return Response({"error": "College not found"}, status=404)

        # 🔹 Check user owns college
        if request.user != college.user:
            return Response({"error": "Permission denied"}, status=403)

        # 🔹 Generate safe filename
        import uuid
        extension = image.name.split(".")[-1]
        filename = f"{uuid.uuid4()}.{extension}"

        # 🔹 Save file
        path = default_storage.save(f"hostels/{college.id}/{filename}", image)
        image_url = default_storage.url(path)

        # 🔹 Make full URL
        full_url = request.build_absolute_uri(image_url)

        return Response({"image_url": full_url}, status=201)

class FilterOptionsAPIView(APIView):
    """
    Returns all dropdown options OR specific filter options dynamically.
    """

    def get_filter_data(self):
        """Collect all filter values in one place to reuse."""
        countries = CollegeProfile.objects.values_list("country", flat=True).distinct()
        states = CollegeProfile.objects.values_list("state", flat=True).distinct()
        districts = CollegeProfile.objects.values_list("district", flat=True).distinct()

        accreditation = (
            CollegeProfile.objects
            .exclude(accreditation_body__isnull=True)
            .exclude(accreditation_body__exact="")
            .values_list("accreditation_body", flat=True)
            .distinct()
        )

        course_levels = [c[0] for c in Course.COURSE_LEVEL_CHOICES]
        main_streams = [c[0] for c in Course.MAIN_STREAM_CHOICES]
        degrees = [c[0] for c in Course.DEGREE_CHOICES]

        specializations = (
            Course.objects
            .exclude(specialization__isnull=True)
            .exclude(specialization__exact="")
            .values_list("specialization", flat=True)
            .distinct()
        )

        return {
            "countries": list(countries),
            "states": list(states),
            "districts": list(districts),
            "accreditation_bodies": list(accreditation),
            "course_levels": course_levels,
            "main_streams": main_streams,
            "degrees": degrees,
            "specializations": list(specializations),
        }

    def get(self, request, filter_name=None):
        all_filters = self.get_filter_data()

        # If /filters/ → return all
        if filter_name is None:
            return Response(all_filters)

        # If /filters/<filter_name>/ → return only that filter
        if filter_name not in all_filters:
            return Response(
                {"error": f"'{filter_name}' is not a valid filter"},
                status=400
            )

        return Response({filter_name: all_filters[filter_name]})
