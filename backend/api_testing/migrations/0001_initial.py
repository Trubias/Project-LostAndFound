from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ApiTestRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('running', 'Running'), ('passed', 'Passed'), ('failed', 'Failed')], default='running', max_length=10)),
                ('requested_by', models.CharField(max_length=150)),
                ('endpoint_id', models.CharField(blank=True, max_length=512)),
                ('http_method', models.CharField(blank=True, max_length=10)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('duration_ms', models.PositiveIntegerField(default=0)),
                ('passed_count', models.PositiveIntegerField(default=0)),
                ('failed_count', models.PositiveIntegerField(default=0)),
                ('results', models.JSONField(default=list)),
                ('output', models.TextField(blank=True)),
            ],
            options={'ordering': ['-started_at']},
        ),
    ]
