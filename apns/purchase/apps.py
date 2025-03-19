from django.apps import AppConfig


class PurchaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purchase'
    verbose_name = '苹果内购管理'

    def ready(self):
        """应用启动时执行的代码"""
        # 导入信号处理器
        import purchase.signals
