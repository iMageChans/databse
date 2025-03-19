import json

from assistant.constants import FREE_RELATIONSHIP_OPTIONS, FREE_NICKNAME_OPTIONS, FREE_PERSONALITY_OPTIONS
from utils.permissions import IsAuthenticatedExternal
from .serializers import AgentInputSerializer
from agent.manager import *
from utils.mixins import *
from rest_framework.viewsets import GenericViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from assistant.models import UsersAssistantTemplates, AssistantTemplates
from engines.models import Engines
from assistant.models import AssistantsConfigs
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentViewSet(CreateModelMixin,
                   GenericViewSet):
    permission_classes = [IsAuthenticatedExternal]

    @swagger_auto_schema(
        operation_summary="发送聊天请求",
        operation_description="向指定的助手发送聊天请求，并获取响应",
        request_body=AgentInputSerializer,
        responses={
            200: openapi.Response(
                description="成功响应",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, description="请求状态"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="响应消息"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'content': openapi.Schema(type=openapi.TYPE_OBJECT, description="响应内容")
                            }
                        )
                    }
                )
            )
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = AgentInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 获取验证后的数据
        validated_data = serializer.validated_data
        user_id = str(request.remote_user.get('id'))
        user_timezone = request.remote_user.get('timezone')
        assistant_name = validated_data.get("assistant_name", "Alice")
        model_name = validated_data.get("model_name")
        users_input = validated_data.get("users_input")
        language = validated_data.get("language")
        user_template_id = validated_data.get("user_template_id", None)
        is_premium = request.remote_user.get('is_premium')

        # 获取用户模板，如果不存在则创建默认模板
        user_template = UsersAssistantTemplates.objects.filter(user_id=user_id).first()
        if not user_template:
            # 获取默认的助手模板
            default_template = AssistantTemplates.objects.filter(is_default=True).first()
            if not default_template:
                return Response({
                    "status": "error",
                    "message": "系统中没有默认模板",
                    "data": {
                        "content": {}
                    }
                }, status=status.HTTP_404_NOT_FOUND)

            # 创建默认的助手配置
            default_config = {
                'user_id': user_id,
                'name': 'Alice',
                'relationship': 'Planner',
                'nickname': 'Buddy',
                'personality': 'Energetic & Upbeat',
                'greeting': '',
                'dialogue_style': '',
                'is_public': False
            }

            # 创建新的默认配置
            config = AssistantsConfigs.objects.create(**default_config)

            # 生成提示词
            prompt_template = default_template.prompt_template
            prompt = prompt_template.replace('{relationship}', config.relationship)
            prompt = prompt.replace('{nickname}', config.nickname)
            prompt = prompt.replace('{personality}', config.personality)
            prompt = prompt.replace('{greeting}', config.greeting or '')
            prompt = prompt.replace('{dialogue_style}', config.dialogue_style or '')

            # 创建用户助手模板
            user_template = UsersAssistantTemplates.objects.create(
                user_id=user_id,
                name='默认模板',
                prompt_template=prompt,
                is_default=True,
                is_premium_template=False
            )

        custom_prompt = user_template.prompt_template

        logger.info(f"参数model_name: {model_name}")

        engine = Engines.objects.get(name=model_name)

        logger.info(f"参数engine.name: {engine.name}")
        logger.info(f"参数engine.base_url: {engine.base_url}")

        assistant = AccountingAssistant(
            api_key=engine.api_key,
            base_url=engine.base_url,
            redis_url="redis://redis:6379/0",
            timezone=user_timezone,
            model=engine.name,
            memory_ttl=3600,
            language=language,
        )

        result = assistant.process_input(user_input=users_input, session_id=str(user_id), ai_config=custom_prompt)

        response_content = result['response']

        # 处理响应内容
        if response_content:  # 确保响应内容不为空
            try:
                # 尝试解析JSON
                print(response_content)
                return Response({
                    "status": "success",
                    "message": "请求已接收",
                    "data": {
                        "content": response_content
                    }
                })
            except json.JSONDecodeError:
                # 如果不是有效的JSON，返回原始内容
                return Response({
                    "status": "success",
                    "message": "请求已接收",
                    "data": {
                        "content": response_content
                    }
                })
        else:
            # 处理空响应
            return Response({
                "status": "success",
                "message": "请求已接收",
                "data": {
                    "content": {}
                }
            })
