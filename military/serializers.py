from collections import OrderedDict
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Division, Order, OrderDivision, CustomUser
from django.urls import reverse

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

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
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser']

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

