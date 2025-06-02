from django.contrib import admin
from military.models import Division, Order, OrderDivision, UserProfile, CustomUser

admin.site.register(Division)
admin.site.register(Order)
admin.site.register(OrderDivision)
admin.site.register(UserProfile)
admin.site.register(CustomUser)