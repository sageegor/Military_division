from datetime import timezone


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from .models import Division, Order, OrderDivision
from .serializers import DivisionSerializer, OrderSerializer, OrderDivisionSerializer
from minio import Minio
from django.conf import settings
import uuid
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

MINIO_URL = "http://127.0.0.1:9000/buckets/militarydivision"

def get_current_user():
    # Фиксированный пользователь для лабораторной работы
    user, _ = User.objects.get_or_create(username='lab_user')
    return user

class DivisionList(APIView):
    def get(self, request):
        queryset = Division.objects.filter(is_active=True)
        serializer = DivisionSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DivisionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DivisionDetail(APIView):
    def get_object(self, pk):
        return get_object_or_404(Division, pk=pk)

    def get(self, request, pk):
        division = self.get_object(pk)
        serializer = DivisionSerializer(division)
        return Response(serializer.data)

    def put(self, request, pk):
        division = self.get_object(pk)
        serializer = DivisionSerializer(division, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        division = self.get_object(pk)
        if division.image_url:
            client = Minio(
                settings.MINIO['ENDPOINT'],
                access_key=settings.MINIO['ACCESS_KEY'],
                secret_key=settings.MINIO['SECRET_KEY'],
                secure=False
            )
            object_name = division.image_url.split('/')[-1]
            client.remove_object(settings.MINIO['BUCKET_NAME'], object_name)
        division.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DivisionImageUpload(APIView):
    def post(self, request, pk):
        division = get_object_or_404(Division, pk=pk)
        file = request.FILES.get('file')

        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        client = Minio(
            settings.MINIO['ENDPOINT'],
            access_key=settings.MINIO['ACCESS_KEY'],
            secret_key=settings.MINIO['SECRET_KEY'],
            secure=False
        )

        if division.image_url:
            old_object = division.image_url.split('/')[-1]
            client.remove_object(settings.MINIO['BUCKET_NAME'], old_object)

        file_extension = os.path.splitext(file.name)[1]
        object_name = f"{uuid.uuid4()}{file_extension}"

        client.put_object(
            settings.MINIO['BUCKET_NAME'],
            object_name,
            file,
            file.size,
            content_type=file.content_type
        )

        division.image_url = f"http://{settings.MINIO['ENDPOINT']}/{settings.MINIO['BUCKET_NAME']}/{object_name}"
        division.save()

        return Response({'image_url': division.image_url})

class OrderList(APIView):
    def get(self, request):
        queryset = Order.objects.exclude(status='deleted')

        # Фильтрация
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(formed_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(formed_at__lte=date_to)

        serializer = OrderSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creator=get_current_user())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderDetail(APIView):
    def get_object(self, pk):
        return get_object_or_404(Order, pk=pk)

    def get(self, request, pk):
        order = self.get_object(pk)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        order = self.get_object(pk)
        serializer = OrderSerializer(order, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        order = self.get_object(pk)
        order.status = 'deleted'
        order.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class OrderForm(APIView):
    def put(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if order.status != 'draft':
            return Response(
                {'error': 'Можно формировать только черновики'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not order.title:
            return Response(
                {'error': 'Не указано название заявки'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'formed'
        order.formed_at = timezone.now()
        order.save()
        return Response(OrderSerializer(order).data)

class OrderComplete(APIView):
    def put(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if order.status != 'formed':
            return Response(
                {'error': 'Можно завершать только сформированные заявки'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'completed'
        order.completed_at = timezone.now()
        order.moderator = get_current_user()
        order.save()
        return Response(OrderSerializer(order).data)

class OrderDivisionList(APIView):
    def get(self, request):
        queryset = OrderDivision.objects.all()
        serializer = OrderDivisionSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OrderDivisionSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.validated_data['order']
            if order.creator != get_current_user():
                raise PermissionDenied("Вы не являетесь создателем этой заявки")
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderDivisionDetail(APIView):
    def get_object(self, pk):
        return get_object_or_404(OrderDivision, pk=pk)

    def get(self, request, pk):
        order_division = self.get_object(pk)
        serializer = OrderDivisionSerializer(order_division)
        return Response(serializer.data)

    def put(self, request, pk):
        order_division = self.get_object(pk)
        if order_division.order.creator != get_current_user():
            raise PermissionDenied("Вы не являетесь создателем этой заявки")

        serializer = OrderDivisionSerializer(order_division, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        order_division = self.get_object(pk)
        if order_division.order.creator != get_current_user():
            raise PermissionDenied("Вы не являетесь создателем этой заявки")
        order_division.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Template views remain the same
def GetOrders(request):
    divisions = Division.objects.filter(is_active=True)
    query = request.GET.get('q', '')

    if query:
        divisions = divisions.filter(name__icontains=query)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'divisions': list(divisions.values('id', 'name', 'description', 'image_url'))
        })

    return render(request, 'orders.html', {'divisions': divisions})

def GetOrder(request, id):
    division = get_object_or_404(Division, id=id)
    return render(request, 'order.html', {'division': division})

def cart_detail(request):
    # Проверяем, авторизован ли пользователь
    if not request.user.is_authenticated:
        # Для неавторизованных пользователей возвращаем пустую корзину
        return render(request, 'cart_detail.html', {
            'cart_items': [],
            'cart_count': 0
        })
    try:
        order = Order.objects.get(creator=request.user, status='draft')
        cart_items = order.orderdivision_set.select_related('division').all()
    except Order.DoesNotExist:
        cart_items = []

    return render(request, 'cart_detail.html', {
        'cart_items': cart_items,
        'cart_count': len(cart_items)
    })

def add_to_cart(request, division_id):
    division = get_object_or_404(Division, id=division_id)

    if request.method == 'POST':
        order, created = Order.objects.get_or_create(
            creator=request.user,
            status='draft'
        )

        order_division, created = OrderDivision.objects.get_or_create(
            order=order,
            division=division,
            defaults={'quantity': 1}
        )

        if not created:
            order_division.quantity += 1
            order_division.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': order.orderdivision_set.count()
            })

        messages.success(request, f'Услуга "{division.name}" добавлена в заявку')

    return redirect(request.META.get('HTTP_REFERER', 'servises'))

def remove_from_cart(request, division_id):
    division = get_object_or_404(Division, id=division_id)

    try:
        order = Order.objects.get(creator=request.user, status='draft')
        order_division = OrderDivision.objects.get(order=order, division=division)

        if order_division.quantity > 1:
            order_division.quantity -= 1
            order_division.save()
        else:
            order_division.delete()

        messages.success(request, f'Услуга "{division.name}" удалена из заявки')
    except (Order.DoesNotExist, OrderDivision.DoesNotExist):
        messages.error(request, 'Ошибка при удалении услуги')

    return redirect('cart_detail')


def get_divisions_partial(request):
    query = request.GET.get('q', '')
    divisions = Division.objects.filter(is_active=True)

    if query:
        divisions = divisions.filter(name__icontains=query)

    return render(request, 'divisions_list.html', {'divisions': divisions})
