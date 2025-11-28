from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator



class CollegeProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='college_profile'
    )

    # --- Basic / Setup Info (collected during initial setup) ---
    college_name = models.CharField(max_length=255)
    college_code = models.CharField(max_length=50, unique=True)  # System-generated unique code
    official_registration_no = models.CharField(max_length=100, blank=True, null=True)  # Optional: provided later
    college_type = models.CharField(
        max_length=50,
        choices=[
            ('government', 'Government'),
            ('private', 'Private'),
            ('autonomous', 'Autonomous'),
        ],
        default='private'
    )
    established_year = models.PositiveIntegerField(blank=True, null=True)
    accreditation_body = models.CharField(max_length=100, blank=True, null=True)

    # --- Contact & Location ---
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField()
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True, null=True)

    # --- Additional / Dashboard Editable Fields ---
    about_college = models.TextField(max_length=2000, blank=True)
    college_logo = models.ImageField(upload_to='colleges/logo/', blank=True, null=True)
    college_image = models.ImageField(upload_to='colleges/main/', blank=True, null=True)
    credential_image = models.ImageField(upload_to='colleges/credentials/', blank=True, null=True)
    landline = models.CharField(max_length=20, blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)

    # --- Status & Meta ---
    verified = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_colleges'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    is_popular = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Helper ---
    def mark_profile_complete(self):
        """
        Automatically mark user's profile as complete
        once setup form is filled.
        """
        required_fields = [self.college_name, self.state, self.email, self.phone, self.country, self.address]
        if all(required_fields):
            self.user.is_profile_complete = True
            self.user.save(update_fields=['is_profile_complete'])

    def __str__(self):
        return self.college_name



class Course(models.Model):
    COURSE_LEVEL_CHOICES = [
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
    ]
    
    MAIN_STREAM_CHOICES = [
        ('engineering', 'Engineering'),
        ('law', 'Law'),
        ('finance', 'Finance'),
        ('medical', 'Medical'),
        ('arts', 'Arts'),
        # Add more as needed
    ]

    DEGREE_CHOICES = [
        ('btech', 'B.Tech'),
        ('mtech', 'M.Tech'),
        ('ba', 'BA'),
        ('llb', 'LLB'),
        ('mba', 'MBA'),
        ('mbbs', 'MBBS'),
        # Add more as relevant for your catalog
    ]

    college = models.ForeignKey(
        CollegeProfile, 
        on_delete=models.CASCADE, 
        related_name='courses',
        to_field='college_code'
    )
    main_stream = models.CharField(max_length=50, choices=MAIN_STREAM_CHOICES)
    degree = models.CharField(max_length=50,default= "B.Tech",choices=DEGREE_CHOICES)
    level = models.CharField(max_length=20, choices=COURSE_LEVEL_CHOICES)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    duration = models.CharField(max_length=100, help_text="e.g., '4 Years', '2 Years'")
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Enter total course fee"
    )
    eligibility = models.TextField(blank=True, help_text="Minimum qualification required")
    description = models.TextField(blank=True, null=True)
    brochure = models.FileField(upload_to='courses/brochures/', blank=True, null=True)

    # ✅ Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['degree', 'specialization']
        unique_together = ['college', 'degree', 'specialization', 'level']

    def __str__(self):
        spec = f" - {self.specialization}" if self.specialization else ""
        return f"{self.get_degree_display()}{spec} ({self.college.college_name})"

class Event(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="events")
    name = models.CharField(max_length=255)
    date = models.DateField()
    location = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="events/images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.college.college_code})"    

class Gallery(models.Model):
    MEDIA_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    college = models.ForeignKey(
        CollegeProfile,
        on_delete=models.CASCADE,
        related_name='gallery_items'
    )

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_CHOICES,
        default='image'
    )

    file = models.FileField(upload_to='college_gallery/')
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Gallery Items"
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return f"{self.media_type} - {self.title or self.file.name}"

class Faculty(models.Model):
    college = models.ForeignKey(
        CollegeProfile,
        on_delete=models.CASCADE,
        related_name='faculties'
    )

    name = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    qualification = models.CharField(max_length=255, blank=True)
    experience = models.CharField(max_length=255, blank=True)  # years or text
    photo = models.ImageField(upload_to='faculty_photos/', blank=True, null=True)
    department = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    bio = models.TextField(blank=True)  # ✔ NEW field to match frontend

    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Faculties'
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} - {self.designation}"
    
class Hostel(models.Model):
    TYPE_CHOICES = [
    ('boys', 'Boys'),
    ('girls', 'Girls'),
]
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name='hostels')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    room_types = models.JSONField(default=dict, blank=True)   # {"single": 10, "double": 20}
    amenities = models.JSONField(default=list, blank=True)    # ["WiFi", "Laundry"]
    fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    description = models.TextField(blank=True)

    # ✅ Multiple hostel images
    images = models.JSONField(default=list, blank=True)  
    # will store array of image URLs after upload

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.college.college_name})"    

