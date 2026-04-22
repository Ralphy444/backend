# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0009_category_menuitem_updated_at_store_description_and_more'),
    ]

    operations = [
        # Rename the Store model to Restaurant
        migrations.RenameModel(
            old_name='Store',
            new_name='Restaurant',
        ),
        # Rename the foreign key field in MenuItem
        migrations.RenameField(
            model_name='menuitem',
            old_name='store',
            new_name='restaurant',
        ),
        # Rename the foreign key field in Order
        migrations.RenameField(
            model_name='order',
            old_name='store',
            new_name='restaurant',
        ),
    ]
