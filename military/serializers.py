from collections import OrderedDict
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Division, Order, OrderDivision, CustomUser
from django.urls import reverse
from django.contrib.auth.hashers import make_password

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'is_staff', 'is_superuser']
        extra_kwargs = {'password': {'write_only': True}, 'username': {'required': True}}

    def validate(self, data):
        if not data.get('username'):
            raise serializers.ValidationError("Username is required")
        return data

    def create(self, validated_data):
        if not validated_data.get('username'):
            validated_data['username'] = validated_data['email'].split('@')[0]

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_staff=validated_data.get('is_staff', False),
            is_superuser=validated_data.get('is_superuser', False)
        )
        return user

class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = '__all__'


class OrderDivisionSerializer(serializers.ModelSerializer):
    division = DivisionSerializer()
    class Meta:
        model = OrderDivision
        fields = ['id', 'division', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    moderator = UserSerializer(read_only=True)
    divisions = OrderDivisionSerializer(many=True, read_only=True, source='orderdivision_set')

    class Meta:
        model = Order
        fields = ['id', 'title', 'status', 'moderator', 'creator', 'divisions']

class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = ['id', 'name', 'description', 'is_active']
        read_only_fields = ['is_active']

    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False
            new_fields[name] = field
        return new_fields

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'is_staff', 'is_superuser']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_staff=validated_data.get('is_staff', False),
            is_superuser=validated_data.get('is_superuser', False)
        )
        return user

class ServicesListSerializer(ServicesSerializer):
    draft_id = serializers.SerializerMethodField()
    in_draft_count = serializers.IntegerField()
    image_url = serializers.SerializerMethodField()

    class Meta(ServicesSerializer.Meta):
        fields = ServicesSerializer.Meta.fields + ['draft_id', 'in_draft_count', 'image_url']

    def get_draft_id(self, obj):
        return self.context.get('draft_id')

    def get_image_url(self, obj):
        if obj.image_url:
            return obj.image_url
        return None

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        required=True
    )

