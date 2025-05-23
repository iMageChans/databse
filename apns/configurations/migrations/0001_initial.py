# Generated by Django 3.2.25 on 2025-03-10 08:46

import configurations.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AppleAppConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='应用的显示名称', max_length=100, verbose_name='应用名称')),
                ('bundle_id', models.CharField(help_text='应用的Bundle ID，例如：com.example.app', max_length=255, unique=True, verbose_name='Bundle ID')),
                ('team_id', models.CharField(help_text='苹果开发者账号的Team ID', max_length=20, verbose_name='Team ID')),
                ('key_id', models.CharField(help_text='APNs认证密钥的ID', max_length=20, verbose_name='Key ID')),
                ('auth_key', models.TextField(help_text='APNs认证密钥内容（.p8文件内容）', verbose_name='认证密钥')),
                ('auth_key_file', models.FileField(blank=True, help_text='上传.p8格式的认证密钥文件', null=True, upload_to='apple_keys/', validators=[configurations.models.validate_p8_file], verbose_name='认证密钥文件')),
                ('is_production', models.BooleanField(default=True, help_text='是否为生产环境，否则为开发环境', verbose_name='生产环境')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '苹果应用配置',
                'verbose_name_plural': '苹果应用配置',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='NotificationTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='模板名称')),
                ('title', models.CharField(max_length=255, verbose_name='通知标题')),
                ('body', models.TextField(verbose_name='通知内容')),
                ('sound', models.CharField(default='default', max_length=50, verbose_name='声音')),
                ('badge', models.IntegerField(default=1, verbose_name='角标数')),
                ('custom_data', models.JSONField(blank=True, default=dict, help_text='JSON格式的自定义数据', verbose_name='自定义数据')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('app_config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='templates', to='configurations.appleappconfiguration', verbose_name='应用配置')),
            ],
            options={
                'verbose_name': '通知模板',
                'verbose_name_plural': '通知模板',
                'ordering': ['-created_at'],
                'unique_together': {('app_config', 'name')},
            },
        ),
    ]
