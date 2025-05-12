from datetime import timezone
from rest_framework import viewsets, status
from django.contrib.auth.models import User
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Division, Order, OrderDivision
from .serializers import DivisionSerializer, OrderSerializer, OrderDivisionSerializer
from minio import Minio
from django.conf import settings
import uuid
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django.contrib import messages




MINIO_URL = "http://127.0.0.1:9000/buckets/militarydivision"
# Create your views here.

cart = {}


def get_current_user():
    # Фиксированный пользователь для лабораторной работы
    user, _ = User.objects.get_or_create(username='lab_user')
    return user


class DivisionViewSet(viewsets.ModelViewSet):
    queryset = Division.objects.filter(is_active=True)
    serializer_class = DivisionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']

    def perform_destroy(self, instance):
        # Удаление изображения из MinIO при удалении услуги
        if instance.image_url:
            client = Minio(
                settings.MINIO['ENDPOINT'],
                access_key=settings.MINIO['ACCESS_KEY'],
                secret_key=settings.MINIO['SECRET_KEY'],
                secure=False
            )
            object_name = instance.image_url.split('/')[-1]
            client.remove_object(settings.MINIO['BUCKET_NAME'], object_name)
        instance.delete()

    @action(detail=True, methods=['post'])
    def upload_image(self, request, pk=None):
        division = self.get_object()
        file = request.FILES.get('file')

        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        client = Minio(
            settings.MINIO['ENDPOINT'],
            access_key=settings.MINIO['ACCESS_KEY'],
            secret_key=settings.MINIO['SECRET_KEY'],
            secure=False
        )

        # Удаляем старое изображение
        if division.image_url:
            old_object = division.image_url.split('/')[-1]
            client.remove_object(settings.MINIO['BUCKET_NAME'], old_object)

        # Загружаем новое
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


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.exclude(status='deleted')
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'created_at', 'formed_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Фильтрация по дате формирования
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            queryset = queryset.filter(formed_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(formed_at__lte=date_to)

        return queryset

    def perform_create(self, serializer):
        serializer.save(creator=get_current_user())

    @action(detail=True, methods=['put'])
    def form(self, request, pk=None):
        order = self.get_object()
        if order.status != 'draft':
            return Response(
                {'error': 'Можно формировать только черновики'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверка обязательных полей
        if not order.title:
            return Response(
                {'error': 'Не указано название заявки'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'formed'
        order.formed_at = timezone.now()
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['put'])
    def complete(self, request, pk=None):
        order = self.get_object()
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


class OrderDivisionViewSet(viewsets.ModelViewSet):
    queryset = OrderDivision.objects.all()
    serializer_class = OrderDivisionSerializer

    def perform_create(self, serializer):
        order = serializer.validated_data['order']
        if order.creator != get_current_user():
            raise PermissionDenied("Вы не являетесь создателем этой заявки")
        serializer.save()

    def perform_update(self, serializer):
        order = serializer.instance.order
        if order.creator != get_current_user():
            raise PermissionDenied("Вы не являетесь создателем этой заявки")
        serializer.save()


def GetOrders(request):
    divisions = Division.objects.filter(is_active=True)  # Берем только активные подразделения
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


class DivisionListCreate(ListCreateAPIView):
    queryset = Division.objects.filter(is_active=True)
    serializer_class = DivisionSerializer

class DivisionRetrieveUpdateDestroy(RetrieveUpdateDestroyAPIView):
    queryset = Division.objects.all()
    serializer_class = DivisionSerializer

class OrderListCreate(ListCreateAPIView):
    queryset = Order.objects.exclude(status='deleted')
    serializer_class = OrderSerializer