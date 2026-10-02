from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0002_paperchunk_embedding'),
    ]

    operations = [
        migrations.AddField(
            model_name='paperchunk',
            name='page_number',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
