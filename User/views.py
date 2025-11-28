# users/views.py
from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model,update_session_auth_hash
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import datetime
import logging
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required
from User.serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    VerifyEmailOTPSerializer,
    VerifyPhoneOTPSerializer,
    ResendEmailOTPSerializer,
    ResendPhoneOTPSerializer,
)
from User.models import EmailOTP, PhoneOTP
from User.permissions import IsAdminOrCounsellor, IsOwnerOrReadOnly

User = get_user_model()

# module logger
logger = logging.getLogger(__name__)

# -----------------------------
# PAGINATION CLASS
# -----------------------------
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


# -----------------------------
# LIST ALL USERS (For Admin/Counsellor)
# -----------------------------
class UserListView(generics.ListAPIView):
    """
    Admin/Counsellor: view all users with pagination, filtering & search.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrCounsellor]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user_type', 'verified', 'email_verified', 'phone_verified']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone']
    ordering_fields = ['date_joined', 'email']


# -----------------------------
# REGISTER VIEW
# -----------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        """
        Register user & trigger email + phone OTP via signals.
        """
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except DRFValidationError as e:
            # Log validation errors so the terminal shows the specific messages
            # (e.detail is usually a dict of field errors)
            logger.warning(
                "Registration validation failed for email=%s phone=%s: %s",
                request.data.get('email'),
                request.data.get('phone'),
                e.detail,
            )
            # Re-raise so DRF will return the normal 400 response
            raise

        result = serializer.save()
        # serializer now performs pre-registration and returns a dict with token
        if isinstance(result, dict) and result.get('pre_token'):
            return Response(result, status=status.HTTP_201_CREATED)
        # fallback (legacy) behavior
        return Response({"message": "User registered successfully. Check your email and phone for OTPs."}, status=status.HTTP_201_CREATED)


# -----------------------------
# VERIFY EMAIL OTP
# -----------------------------
class VerifyEmailOTPView(generics.GenericAPIView):
    serializer_class = VerifyEmailOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Body:
        {
          "email": "user@example.com",
          "otp": "123456"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        return Response(response, status=status.HTTP_200_OK)


# -----------------------------
# VERIFY PHONE OTP
# -----------------------------
class VerifyPhoneOTPView(generics.GenericAPIView):
    serializer_class = VerifyPhoneOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Body:
        {
          "phone": "9876543210",
          "otp": "123456"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        return Response(response, status=status.HTTP_200_OK)


# -----------------------------
# LOGIN VIEW
# -----------------------------
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Body:
        {
          "email": "user@example.com",
          "password": "password"
        }
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        tokens = RefreshToken.for_user(user)
        return Response({
            "access": str(tokens.access_token),
            "refresh": str(tokens),
            "user": UserSerializer(user).data
        })


# -----------------------------
# USER PROFILE VIEW
# -----------------------------
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    queryset = User.objects.all()

    def get_object(self):
        user_id = self.request.query_params.get('user_id')
        if user_id and self.request.user.user_type in ['admin', 'counsellor']:
            return User.objects.get(id=user_id)
        return self.request.user


# -----------------------------
# CHANGE PASSWORD (logged-in)
# -----------------------------

class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not user.check_password(current_password):
            return Response({"error": "Current password is incorrect."}, status=400)

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)

        return Response({"message": "Password updated successfully!"}, status=200)


# -----------------------------
# PASSWORD RESET REQUEST (forgot password)
# -----------------------------
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    RATE_LIMIT_MINUTES = 15
    MAX_ATTEMPTS = 5

    def post(self, request):
        """
        Body: { "email": "user@example.com" }
        Rate-limited: MAX_ATTEMPTS per RATE_LIMIT_MINUTES using EmailOTP entries
        """
        # validate incoming email first via serializer.validate_email
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        # rate limiting using existing EmailOTP records
        recent = EmailOTP.objects.filter(
            user=user,
            created_at__gte=timezone.now() - datetime.timedelta(minutes=self.RATE_LIMIT_MINUTES)
        )

        if recent.count() >= self.MAX_ATTEMPTS:
            return Response(
                {"error": f"Too many password reset requests. Try again after {self.RATE_LIMIT_MINUTES} minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # serializer.save() will create EmailOTP and send mail
        response = serializer.save()
        return Response(response, status=status.HTTP_200_OK)


# -----------------------------
# PASSWORD RESET CONFIRM (forgot password)
# -----------------------------
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Body:
        {
          "email": "user@example.com",
          "otp": "123456",
          "new_password": "NewPass@123",
          "confirm_password": "NewPass@123"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        return Response(response, status=status.HTTP_200_OK)


# -----------------------------
# RESEND EMAIL OTP (with rate limiting)
# -----------------------------
class ResendEmailOTPView(generics.GenericAPIView):
    serializer_class = ResendEmailOTPSerializer
    permission_classes = [permissions.AllowAny]

    RATE_LIMIT_MINUTES = 10
    MAX_ATTEMPTS = 3

    def post(self, request):
        """
        Body: { "email": "user@example.com" }
        Rate limiting uses EmailOTP entries in last RATE_LIMIT_MINUTES
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        recent = EmailOTP.objects.filter(
            user=user,
            created_at__gte=timezone.now() - datetime.timedelta(minutes=self.RATE_LIMIT_MINUTES)
        )

        if recent.count() >= self.MAX_ATTEMPTS:
            return Response(
                {"error": f"Too many requests. Try again after {self.RATE_LIMIT_MINUTES} minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # perform resend (serializer.save() creates new EmailOTP and sends email)
        response = serializer.save()
        return Response(response, status=status.HTTP_200_OK)


# -----------------------------
# RESEND PHONE OTP (with rate limiting)
# -----------------------------
class ResendPhoneOTPView(generics.GenericAPIView):
    serializer_class = ResendPhoneOTPSerializer
    permission_classes = [permissions.AllowAny]

    RATE_LIMIT_MINUTES = 10
    MAX_ATTEMPTS = 3

    def post(self, request):
        """
        Body: { "phone": "9876543210" }
        Rate limiting uses PhoneOTP entries in last RATE_LIMIT_MINUTES
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        user = User.objects.get(phone=phone)

        recent = PhoneOTP.objects.filter(
            user=user,
            created_at__gte=timezone.now() - datetime.timedelta(minutes=self.RATE_LIMIT_MINUTES)
        )

        if recent.count() >= self.MAX_ATTEMPTS:
            return Response(
                {"error": f"Too many OTP requests. Try again after {self.RATE_LIMIT_MINUTES} minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # serializer.save() creates new PhoneOTP and prints/sends SMS as implemented
        response = serializer.save()
        return Response(response, status=status.HTTP_200_OK)

class CheckProfileStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "user_type": user.user_type,
            "is_profile_complete": user.is_profile_complete
        })    
    

 # -----------------------------
# Logout Admin and Redirect to Frontend
# -----------------------------   
@staff_member_required
def admin_logout_redirect(request):
        """
        Logout an admin user and redirect to the frontend landing page.

        Notes:
        - `staff_member_required` wraps this view and will redirect to the admin
            login page if the caller is not authenticated as a staff user. In API
            contexts using token/JWT auth the decorator can redirect to the admin
            login instead of the frontend. To avoid surprising redirects we ensure
            we only redirect to the frontend for authenticated staff users.
        - This view clears the session (Django logout). If you use JWTs this
            does not invalidate tokens; implement token blacklisting if needed.
        """
        user = getattr(request, 'user', None)
        # Double-check staff status (the decorator normally enforces this)
        if not user or not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_staff', False):
                # If the requester is not an authenticated staff user, send them to admin login
                from django.contrib.admin.views.decorators import redirect_to_login
                return redirect_to_login(request.get_full_path())

        # Clear the session and redirect to frontend landing page
        logout(request)
        frontend_url = getattr(settings, "FRONTEND_BASE_URL", "http://127.0.0.1:5502")
        return redirect(f"{frontend_url.rstrip('/')}/index.html")