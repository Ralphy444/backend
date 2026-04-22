from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0025_suki_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='scheduled_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
