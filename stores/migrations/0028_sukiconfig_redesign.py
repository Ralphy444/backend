from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0027_sukiconfig'),
    ]

    operations = [
        migrations.RemoveField(model_name='sukiconfig', name='pesos_per_point_earn'),
        migrations.RemoveField(model_name='sukiconfig', name='pesos_per_point_redeem'),
        migrations.AddField(
            model_name='sukiconfig',
            name='points_per_peso',
            field=models.DecimalField(
                max_digits=8, decimal_places=4, default=0.05,
                help_text='Points earned per ₱1 spent. Examples: 0.05 = 1pt per ₱20 | 0.1 = 1pt per ₱10 | 0.5 = 1pt per ₱2 | 1.0 = 1pt per ₱1'
            ),
        ),
        migrations.AddField(
            model_name='sukiconfig',
            name='minimum_points_to_redeem',
            field=models.PositiveIntegerField(
                default=100,
                help_text='Minimum points a customer must have before they can redeem. Example: 100'
            ),
        ),
        migrations.AddField(
            model_name='sukiconfig',
            name='peso_value_per_point',
            field=models.DecimalField(
                max_digits=8, decimal_places=2, default=0.20,
                help_text='How much ₱ discount 1 point gives. Examples: 0.20 = 1pt = ₱0.20 | 1.0 = 1pt = ₱1 | 2.0 = 1pt = ₱2'
            ),
        ),
    ]
