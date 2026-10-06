from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Q
from .serializers import UserSerializer, UserProfileSerializer, RegisterSerializer

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not isinstance(request.data, dict):
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)

        username = request.data.get("username")
        password = request.data.get("password")
        
        user = authenticate(username=username, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user": UserSerializer(user).data
            })
        else:
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if hasattr(request.user, 'auth_token'):
                request.user.auth_token.delete()
            elif request.auth and hasattr(request.auth, 'delete'):
                request.auth.delete()
        except Exception:
            pass
        return Response({"success": "Successfully logged out."}, status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class TestProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Hello, {request.user.username}! You are authenticated."})

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        data = dict(serializer.data)

        # Calculate project counts and friends counts cleanly
        from projects.models import Project, ProjectMember
        from .models import Friendship

        owned_count = Project.objects.filter(owner=user).count()
        member_count = ProjectMember.objects.filter(user=user).exclude(project__owner=user).count()
        total_projects = owned_count + member_count

        friends_count = Friendship.objects.filter(
            Q(user=user, status='ACCEPTED') | Q(friend=user, status='ACCEPTED')
        ).count()

        data["projects_count"] = total_projects
        data["friends_count"] = friends_count

        return Response(data)

