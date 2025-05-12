from rest_framework import serializers
from .models import Division, Order, OrderDivision
from django.contrib.auth.models import User


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
        fields = '__all__'
        read_only_fields = ['status', 'created_at', 'creator', 'moderator',]

