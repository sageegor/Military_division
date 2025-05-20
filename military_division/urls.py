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
from django.urls import path, include, re_path
from military import views

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('servises/', views.GetOrders, name='servises'),
                  path('order/<int:id>/', views.GetOrder, name='order_url'),
                  path('cart/', views.cart_detail, name='cart_detail'),
                  path('add-to-cart/<int:division_id>/', views.add_to_cart, name='add_to_cart'),
                  path('remove-from-cart/<int:division_id>/', views.remove_from_cart, name='remove_from_cart'),
                  path('get_divisions_partial/', views.get_divisions_partial, name='get_divisions_partial'),

                  # API endpoints
                  path('api/divisions/', views.DivisionList.as_view(), name='division-list'),
                  path('api/divisions/<int:pk>/', views.DivisionDetail.as_view(), name='division-detail'),
                  path('api/divisions/<int:pk>/upload-image/', views.DivisionImageUpload.as_view(),
                       name='division-upload-image'),
                  path('api/orders/', views.OrderList.as_view(), name='order-list'),
                  path('api/orders/<int:pk>/', views.OrderDetail.as_view(), name='order-detail'),
                  path('api/orders/<int:pk>/form/', views.OrderForm.as_view(), name='order-form'),
                  path('api/orders/<int:pk>/complete/', views.OrderComplete.as_view(), name='order-complete'),
                  path('api/order-divisions/', views.OrderDivisionList.as_view(), name='orderdivision-list'),
                  path('api/order-divisions/<int:pk>/', views.OrderDivisionDetail.as_view(),name='orderdivision-detail'),

              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

