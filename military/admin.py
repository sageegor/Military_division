from django.contrib import admin
from .models import Division, Order, OrderDivision, UserProfile


admin.site.register(Division)
admin.site.register(Order)
admin.site.register(OrderDivision)
admin.site.register(UserProfile)