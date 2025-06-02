from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.contrib.auth.models import User, PermissionsMixin, UserManager
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.utils import timezone
class Division(models.Model):
    name = models.CharField("Название", max_length=255)
    description = models.TextField("Описание")
    image_url = models.URLField("Ссылка на изображение", blank=True, null=True)
    is_active = models.BooleanField("Активно", default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления',auto_now=True )
    class Meta:
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"

    def __str__(self):
        return self.name
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_moderator = models.BooleanField('Модератор', default=False)

    def __str__(self):
        return f"Профиль {self.user.username}"

class Order(models.Model):
    title_choices = [
        ('Leningrad Military District', 'Ленинградский военный округ'),
        ('Moscow Military District', 'Московский военный округ'),
        ('Central Military District', 'Центральный военный округ'),
        ('Southern Military District', 'Южный военный округ '),
        ('Eastern Military District', 'Восточный Военный округ'),
        ('None', 'Нет')
     ]

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('formed', 'Сформирована'),
        ('completed', 'Завершена'),
        ('rejected', 'Отклонена'),
        ('deleted', 'Удалена')
    ]

    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,verbose_name='Создатель',related_name='created_orders')
    title = models.CharField (verbose_name='Округ', max_length=50, choices=title_choices, default='None')

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.title}"

class OrderDivision(models.Model):
    order = models.ForeignKey(Order,on_delete=models.PROTECT,verbose_name='Заявка')
    division = models.ForeignKey(Division,on_delete=models.PROTECT,verbose_name='Подразделение')
    quantity = models.PositiveIntegerField('Количество', default=1)
    is_main = models.BooleanField('Основное', default=False)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Связь заявки и подразделения'
        verbose_name_plural = 'Связи заявок и подразделений'
        unique_together = ('order', 'division')

    def __str__(self):
        return f"{self.order} - {self.division} (x{self.quantity})"


class NewUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    username = models.CharField (max_length=50, unique=True, default='default_username')
    email = models.EmailField(("email адрес"), unique=True)
    password = models.CharField(max_length=255, verbose_name="Пароль")
    is_staff = models.BooleanField(default=False, verbose_name="Является ли пользователь менеджером?")
    is_superuser = models.BooleanField(default=False, verbose_name="Является ли пользователь админом?")
    is_active = models.BooleanField(default=True)  # Обязательное поле!

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = NewUserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            # Генерируем username из email, если не указан
            self.username = self.email.split('@')[0]
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'military_customuser'

    def __str__(self):
        return self.email