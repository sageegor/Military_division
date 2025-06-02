from sqlite3 import IntegrityError

from .models import Division, Order, OrderDivision, CustomUser
from .serializers import DivisionSerializer, OrderSerializer, OrderDivisionSerializer, UserSerializer, ServicesListSerializer, ServicesSerializer, LoginSerializer
from datetime import timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.forms import IntegerField
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from military_division.permissions import IsAdmin, IsManager
from minio import Minio
from multiprocessing import Value
from rest_framework import status, permissions, viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
import os
#import redis
import uuid

MINIO_URL = "http://127.0.0.1:9000/buckets/militarydivision"

# Инициализация Redis
#redis_client = redis.Redis(
   # host=settings.REDIS_HOST,
    #port=settings.REDIS_PORT,
    #db=settings.REDIS_DB,
    #socket_connect_timeout=3
#)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'status': 'success',
            'user_id': user.id,
            'username': user.username
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='post',
    request_body=LoginSerializer,
    responses={
        200: 'Successful authentication',
        401: 'Invalid credentials'
    }
)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    user = authenticate(request, email=email, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'status': 'success',
            'user_id': user.id,
            'token': token.key,
        })
    return Response({'error': 'Invalid credentials'}, status=401)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    # Удаляем токен, если он существует
    Token.objects.filter(user=request.user).delete()
    logout(request)  # Стандартный выход Django
    return Response({'status': 'success'})

class IsAuthenticatedOrReadServices(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'GET' and view.__class__.__name__ == 'ServicesListView':
            return True
        return request.user and request.user.is_authenticated

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
            return Response({
                'status': 'success',
                'user_id': user.id,
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response({
                'status': 'error',
                'message': 'Username or email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

class ServicesListView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_storage=None):
        session_id = request.COOKIES.get('session_id')

        if not session_id or not session_storage.get(session_id):
            return Response({'error': 'Invalid session'}, status=401)

        # Фильтрация услуг
        divisions = Division.objects.filter(is_active=True)

        # Получаем черновик заявки пользователя
        user_draft = Order.objects.filter(
            creator_id=request.user.id,
            status='draft'
        ).first()

        # Аннотируем количество услуг в заявке
        if user_draft:
            divisions = divisions.annotate(
                in_draft_count=Count(
                    'orderservices',
                    filter=Q(orderdivision__order=user_draft)
                ))
        else:
            divisions = divisions.annotate(in_draft_count=Value(0, output_field=IntegerField()))

        serializer = ServicesListSerializer(divisions, many=True, context={
            'draft_id': user_draft.id if user_draft else None})
        return Response(serializer.data)

    @swagger_auto_schema(request_body=ServicesSerializer)
    def post(self, request):
        serializer = ServicesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ServicesDetailView(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action in ['get']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    def method_permission_classes(classes):
        def decorator(func):
            def decorated_func(self, *args, **kwargs):
                self.permission_classes = classes
                self.check_permissions(self.request)
                return func(self, *args, **kwargs)

            return decorated_func

        return decorator

    def get(self, request, pk):
        service = get_object_or_404(Division, pk=pk, is_active=True)
        serializer = ServicesSerializer(service)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=ServicesSerializer)
    def put(self, request, pk):
        service = get_object_or_404(Division, pk=pk)
        serializer = ServicesSerializer(service, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=ServicesSerializer)
    def delete(self, request, pk):
        service = get_object_or_404(Division, pk=pk)

        service.is_active = False
        service.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

def get_current_user():
    # Фиксированный пользователь для лабораторной работы
    user, _ = User.objects.get_or_create(username='lab_user')
    return user

class DivisionList(APIView):
    permissions_classes = [AllowAny] # Разрешаем доступ без авторизации

    @swagger_auto_schema(
        operation_description="Получить список всех подразделений (доступ без авторизации)",
        security=[]  # Явно отключаем требования безопасности для этого метода
    )
    def get(self, request):
        queryset = Division.objects.filter(is_active=True)
        serializer = DivisionSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        # POST оставляем только для авторизованных
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        serializer = DivisionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def divisions_list(request):
        if request.method == 'OPTIONS':
            response = JsonResponse({})
            response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type'
            return response

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

@permission_classes([IsAuthenticated])
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

@login_required
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

@login_required
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
