import json

from utils.permissions import IsAuthenticatedExternal
from .serializers import AgentInputSerializer
from agent.manager import *
from utils.mixins import *
from rest_framework.viewsets import GenericViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from assistant.models import UsersAssistantTemplates
from engines.models import Engines
from django.core.exceptions import ObjectDoesNotExist


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

        custom_prompt = UsersAssistantTemplates.objects.filter(user_id=user_id).first().prompt_template

        engine = Engines.objects.get(name=model_name)

        try:
            # 场景1：提供模板ID且是高级用户
            if user_template_id and is_premium:
                template = UsersAssistantTemplates.objects.get(
                    user_id=user_id,
                    id=user_template_id,
                    is_premium_template=True
                )
                return template.prompt_template, None

            # 场景2：提供模板ID且非高级用户
            elif user_template_id and not is_premium:
                template = UsersAssistantTemplates.objects.get(
                    user_id=user_id,
                    id=user_template_id,
                    is_premium_template=False
                )
                return template.prompt_template, None

            # 场景3：未提供模板ID，尝试获取默认模板
            else:
                try:
                    template = UsersAssistantTemplates.objects.get(
                        user_id=user_id,
                        is_default=True
                    )
                    return template.prompt_template, None
                except ObjectDoesNotExist:
                    error = "用户未设置默认模板"

        except ObjectDoesNotExist as e:
            error = f"指定模板不存在: {str(e)}"
        except Exception as e:
            error = f"系统错误: {str(e)}"

        assistant = AccountingAssistant(
            api_key=engine.api_key,
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
