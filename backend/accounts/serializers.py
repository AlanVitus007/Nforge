from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Friendship

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'is_superuser')
        read_only_fields = ('is_staff', 'is_superuser')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class SafeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class FriendshipSerializer(serializers.ModelSerializer):
    user = SafeUserSerializer(read_only=True)
    friend = SafeUserSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ('id', 'user', 'friend', 'status', 'created_at', 'updated_at')
