from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [
        ('military', '0002_alter_division_options_alter_order_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='division',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='division',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
