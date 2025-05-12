from django.db import models
from django.contrib.auth.models import User
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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_moderator = models.BooleanField('Модератор', default=False)

    def __str__(self):
        return f"Профиль {self.user.username}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('formed', 'Сформирована'),
        ('completed', 'Завершена'),
        ('rejected', 'Отклонена'),
        ('deleted', 'Удалена')
    ]

    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    creator = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Создатель',related_name='created_orders')

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']


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

