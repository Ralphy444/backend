from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0026_order_scheduled_time'),
    ]

    operations = [
        migrations.CreateModel(
            name='SukiConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pesos_per_point_earn', models.DecimalField(
                    max_digits=8, decimal_places=2, default=10.00,
                    help_text='How many pesos the customer must spend to earn 0.5 points. Default: ₱10 = 0.5 pts'
                )),
                ('pesos_per_point_redeem', models.DecimalField(
                    max_digits=8, decimal_places=2, default=20.00,
                    help_text='How many pesos discount 1 point gives. Default: 1 pt = ₱20'
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Suki Points Configuration',
                'verbose_name_plural': 'Suki Points Configuration',
            },
        ),
    ]
