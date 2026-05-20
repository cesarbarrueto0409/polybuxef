from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='racha_actual',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='usuario',
            name='ultima_racha',
            field=models.DateField(blank=True, null=True),
        ),
    ]
