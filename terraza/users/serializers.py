from rest_framework import serializers
from .models import UserAccount, Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'image',
            'gender',
            'country',
            'state',
            'address',
            'pid',
            'date_created',
        ]
        read_only_fields = ['pid', 'date_created']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = UserAccount
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'phone',
            'is_active',
            'is_staff',
            'profile',
        ]
        read_only_fields = ['is_active', 'is_staff']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    profile = ProfileSerializer(required=False)

    class Meta:
        model = UserAccount
        fields = [
            'email',
            'first_name',
            'last_name',
            'phone',
            'password',
            'profile',
        ]

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        password = validated_data.pop('password')
        user = UserAccount.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        if profile_data:
            Profile.objects.update_or_create(user=user, defaults=profile_data)
        else:
            # Create empty profile if not provided (optional, already handled by signal)
            Profile.objects.get_or_create(user=user)

        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = UserAccount
        fields = ['email', 'first_name', 'last_name', 'phone', 'profile']
        read_only_fields = ['email']  # Usually email shouldn't be changed here

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create profile fields
        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        return instance