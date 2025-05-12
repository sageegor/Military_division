"""
URL configuration for military_division project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from military import views
from rest_framework.routers import DefaultRouter
from military.views import DivisionViewSet, OrderViewSet, OrderDivisionViewSet

router = DefaultRouter()
router.register(r'divisions', DivisionViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'order-divisions', OrderDivisionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('servises/', views.GetOrders, name='servises'),
    path('order/<int:id>/', views.GetOrder, name='order_url'),
    path('cart/',views.cart_detail,name='cart_detail'),
    path('api/divisions/', views.DivisionListCreate.as_view(), name='division-list'),
    path('api/divisions/<int:pk>/', views.DivisionRetrieveUpdateDestroy.as_view(), name='division-detail'),
    path('api/orders/', views.OrderListCreate.as_view(), name='order-list'),
    path('add-to-cart/<int:division_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:division_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('api/', include(router.urls)),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

