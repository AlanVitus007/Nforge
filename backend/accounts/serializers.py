import re
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers
from .models import Friendship

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
        read_only_fields = ('is_staff', 'is_superuser')

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active', 'is_staff', 'is_superuser')
        read_only_fields = ('id', 'date_joined', 'is_active', 'is_staff', 'is_superuser')

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        min_length=3,
        max_length=150,
        required=True,
        error_messages={
            'blank': 'Username is required.',
            'required': 'Username is required.',
            'min_length': 'Username must be at least 3 characters long.',
            'max_length': 'Username cannot exceed 150 characters.',
        }
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
        read_only_fields = ('id', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')

    def validate_username(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Username is required.')
        if len(cleaned) < 3:
            raise serializers.ValidationError('Username must be at least 3 characters long.')
        if len(cleaned) > 150:
            raise serializers.ValidationError('Username cannot exceed 150 characters.')

        if not re.match(r'^[a-zA-Z0-9_.-]+$', cleaned):
            raise serializers.ValidationError(
                'Enter a valid username. Allowed characters are letters, numbers, and ./_/-.'
            )

        instance = getattr(self, 'instance', None)
        qs = User.objects.filter(username__iexact=cleaned)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A user with this username already exists.')

        return cleaned

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        raw_data = self.initial_data
        errors = {}

        if instance and isinstance(raw_data, dict):
            # Explicitly reject attempts to change protected fields
            if 'first_name' in raw_data and raw_data['first_name'] != instance.first_name:
                errors['first_name'] = 'First name cannot be changed through the profile endpoint.'

            if 'last_name' in raw_data and raw_data['last_name'] != instance.last_name:
                errors['last_name'] = 'Last name cannot be changed through the profile endpoint.'

            if 'email' in raw_data and str(raw_data['email']).strip().lower() != instance.email.lower():
                errors['email'] = 'Email address cannot be changed through the profile endpoint.'

            if 'is_staff' in raw_data and bool(raw_data['is_staff']) != instance.is_staff:
                errors['is_staff'] = 'Staff privileges cannot be modified.'

            if 'is_superuser' in raw_data and bool(raw_data['is_superuser']) != instance.is_superuser:
                errors['is_superuser'] = 'Superuser privileges cannot be modified.'

            if 'password' in raw_data:
                errors['password'] = 'Password cannot be changed through the profile endpoint.'

            if 'id' in raw_data and str(raw_data['id']) != str(instance.id):
                errors['id'] = 'User ID cannot be modified.'

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.save(update_fields=['username'])
        return instance

class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        max_length=150,
        required=True,
        error_messages={
            'blank': 'First name is required.',
            'required': 'First name is required.',
        }
    )
    last_name = serializers.CharField(
        max_length=150,
        required=True,
        error_messages={
            'blank': 'Last name is required.',
            'required': 'Last name is required.',
        }
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            'blank': 'Email address is required.',
            'required': 'Email address is required.',
            'invalid': 'Enter a valid email address.',
        }
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': 'Password is required.',
            'required': 'Password is required.',
        }
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': 'Please confirm your password.',
            'required': 'Please confirm your password.',
        }
    )

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'email', 'password', 'confirm_password')
        extra_kwargs = {
            'username': {
                'error_messages': {
                    'blank': 'Username is required.',
                    'required': 'Username is required.',
                }
            }
        }

    def validate_first_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('First name is required.')
        return cleaned

    def validate_last_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Last name is required.')
        return cleaned

    def validate_username(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Username is required.')
        if User.objects.filter(username__iexact=cleaned).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return cleaned

    def validate_email(self, value):
        cleaned = value.strip().lower()
        if not cleaned:
            raise serializers.ValidationError('Email address is required.')
        try:
            validate_email(cleaned)
        except DjangoValidationError:
            raise serializers.ValidationError('Enter a valid email address.')
        if User.objects.filter(email__iexact=cleaned).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return cleaned

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})

            if len(password) < 8:
                raise serializers.ValidationError({'password': 'Password must be at least 8 characters long.'})

            try:
                validate_password(password)
            except DjangoValidationError as err:
                raise serializers.ValidationError({'password': list(err.messages)})

        # Explicitly disallow any injected privilege escalation fields
        attrs.pop('is_staff', None)
        attrs.pop('is_superuser', None)

        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        validated_data.pop('is_staff', None)
        validated_data.pop('is_superuser', None)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
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
