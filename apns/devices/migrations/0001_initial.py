# Generated by Django 3.2.25 on 2025-03-10 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(db_index=True, help_text='UserCenter的用户ID', verbose_name='用户ID')),
                ('device_id', models.CharField(max_length=255)),
                ('device_token', models.CharField(max_length=255)),
                ('send_time', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '设备管理',
                'verbose_name_plural': '设备管理',
                'ordering': ['-created_at'],
            },
        ),
    ]
