from datetime import datetime
import pytz
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema.runnable import (
    RunnablePassthrough,
    RunnableLambda,
    RunnableParallel
)
from langchain_community.chat_message_histories import RedisChatMessageHistory
from redis import ConnectionPool, Redis
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AccountingAssistant:
    """
    记账助手类，提供自然语言记账和对话功能
    """

    # 默认的AI配置
    DEFAULT_AI_CONFIG = {
        "ai_personality": "记账助手并且也是一个用户可以陪伴的人，所以不不仅仅是只会记账",
        "greeting": "当用户输入如果没有交易记录的时候需要幽默的回应以及聊天，请按以下规则处理用户输入",
        "relationship_context": "",
        "tone_guidance": "",
        "response_style": "给予幽默的回应"
    }

    # 基础提示模板
    DEFAULT_PROMPT_TEMPLATE = """
    你是一个{ai_personality}，当前时间是{eastern_time}，{greeting}

    {relationship_context}

    请使用{language}回复用户。

    输出为JSON格式，content包含以下字段ai_output，random，emoji，transactions，其中transactions数组包含字段type，amount，category，note，random，emoji，date。如果没有交易信息返回transactions：[]

    重要提示：请确保你的回复具有多样性和创造性，即使用户输入相同的内容，也应该提供不同的回复。{tone_guidance}

    1. **交易识别**：自动分离连续交易（如"午餐+打车费"拆分为两笔独立记录）
    2. **分类标准**：
       - 支出分类：Food、Clothes、Transport、Vegetables、Snacks、Groceries、Shopping、Fruits、Sports、Communication、Study、Beauty、Pets、Entertainment、Digital、Gifts、Travel、Household、Others
       - 收入分类：Salary、Part-time Job、Investments、Others
    3. **emoji分类标准**：
        - confused (困惑、不解)
        - excited (兴奋、激动)
        - funny (有趣、幽默)
        - joy (快乐、愉悦)
        - motivational (激励、鼓舞)
        - relaxing (放松、平静)
        - sad (悲伤、遗憾)
        - random (如果无法确定)
    4. **字段要求**：
        * ai_output：阅读用户输入，然后{response_style}
        * random： 1-90的随机数，只返回数字
        * emoji：按照emoji分类标准选一个返回，只需返回对应的英文单词，不需要解释。
        * transactions：数组，以下是transactions的字段
           * type：必填（expense/income，需要识别出用户输入的语言是expense还是income
           * amount：强制转为数字类型（如"30元"→30.00）
           * category：必须使用上述英文分类，无匹配则用Others
           * note：分类为Others时固定写"没有明确交易信息"，其他情况提取关键词
           * date：{eastern_time}
    5. {eastern_time}这个是现在的时间

    聊天历史:
    {chat_history}
    ---
    用户输入: {content}
    """

    def __init__(self,
                 api_key=None,
                 base_url=None,
                 redis_url=None,
                 timezone=None,
                 model="gpt-3.5-turbo",
                 temperature=0.8,
                 memory_ttl=24 * 3600,
                 log_level=logging.INFO,
                 prompt_template=None,
                 language="zh-cn"):
        """
        初始化记账助手

        参数:
            api_key (str, 可选): OpenAI API密钥，默认从环境变量获取
            redis_url (str, 可选): Redis连接URL，默认从环境变量获取
            timezone (str, 可选): 时区，默认从环境变量获取
            model (str, 可选): 使用的语言模型，默认为gpt-3.5-turbo
            temperature (float, 可选): 模型温度参数，控制创造性，默认为0.8
            memory_ttl (int, 可选): 记忆过期时间(秒)，默认为24小时
            log_level (int, 可选): 日志级别，默认为INFO
            prompt_template (str, 可选): 自定义提示模板，默认使用内置模板
            language (str, 可选): AI回复使用的语言，默认为中文(zh-CN)
        """
        # 配置日志级别
        logger.setLevel(log_level)

        # 设置API密钥
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

        # 设置Redis连接
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://192.168.1.172:6379/0")
        self.redis_pool = ConnectionPool.from_url(self.redis_url, decode_responses=True)
        self.redis_client = Redis(connection_pool=self.redis_pool)

        # 设置时区
        timezone_str = timezone or os.getenv("TIMEZONE", 'America/Toronto')
        self.timezone = pytz.timezone(timezone_str)

        # 设置记忆TTL
        self.memory_ttl = memory_ttl

        # 设置提示模板
        self.base_prompt_template = prompt_template or self.DEFAULT_PROMPT_TEMPLATE

        # 设置语言
        self.language = language

        logger.info(f"当前bas_url: {base_url}")

        # 初始化LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=512,
            base_url=base_url,
            api_key=self.api_key,
            streaming=True,
        )

        # 会话链缓存
        self._chain_cache = {}

    def get_eastern_time(self) -> str:
        """获取格式化的时间"""
        return datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S")

    def get_memory(self, session_id: str) -> ConversationBufferMemory:
        """获取会话记忆实例"""
        try:
            return ConversationBufferMemory(
                memory_key="chat_history",
                chat_memory=self._create_chat_history(session_id),
                return_messages=True,
                input_key="content"
            )
        except Exception as e:
            logger.error(f"创建记忆实例失败: {e}")
            # 返回一个内存中的备用记忆实例
            return ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                input_key="content"
            )

    def _create_chat_history(self, session_id: str):
        """创建增强的聊天历史存储"""
        return EnhancedRedisChatMessageHistory(
            session_id=session_id,
            url=self.redis_url,
            ttl=self.memory_ttl
        )

    def create_prompt_template(self, ai_config=None):
        """
        创建自定义的提示模板

        参数:
            ai_config (dict, 可选): AI配置参数，包括性格、关系等

        返回:
            PromptTemplate: 定制化的提示模板
        """
        # 合并默认配置和自定义配置
        config = self.DEFAULT_AI_CONFIG.copy()
        if ai_config:
            config.update(ai_config)

        # 创建提示模板
        return PromptTemplate.from_template(self.base_prompt_template)

    def parse_ai_config_string(self, config_string):
        """
        解析用户提供的配置字符串，转换为AI配置字典

        参数:
            config_string (str): 用户提供的配置字符串

        返回:
            dict: 解析后的AI配置字典
        """
        if not config_string:
            return None

        config = {}

        # 尝试解析配置字符串
        try:
            lines = config_string.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # 映射用户配置键到系统配置键
                    if key == "你的性格":
                        config["ai_personality"] = f"{value}记账助手"
                    elif key == "你与用户的关系":
                        config["relationship_context"] = f"我们的关系是{value}关系。"
                    elif key == "你对用户的问候语":
                        config["greeting"] = value
                    elif key == "你对用户的说话方式":
                        config["response_style"] = f"以{value}的方式回应"
                    elif key == "你对用户的称呼":
                        # 将称呼添加到问候语中
                        greeting = config.get("greeting", "")
                        if greeting:
                            config["greeting"] = f"{greeting}，我会称呼你为{value}"
                        else:
                            config["greeting"] = f"我会称呼你为{value}"

            # 如果没有设置问候语，使用默认问候语
            if "greeting" not in config:
                config["greeting"] = self.DEFAULT_AI_CONFIG["greeting"]

            # 添加记账助手的基本功能描述
            if "ai_personality" in config:
                config["ai_personality"] += "，我可以帮你记账并陪伴聊天"

            # 设置语气指导
            if "你对用户的说话方式" in config:
                style = config.get("你对用户的说话方式", "")
                config["tone_guidance"] = f" 请保持{style}的语气。"

        except Exception as e:
            logger.error(f"解析配置字符串失败: {e}", exc_info=True)
            return None

        return config

    def build_chain(self, sessions_id: str, ai_config=None):
        """
        构建对话链

        参数:
            sessions_id (str): 会话ID
            ai_config (dict, 可选): AI配置参数

        返回:
            callable: 处理用户输入的函数
        """
        memory = self.get_memory(sessions_id)

        # 创建自定义提示模板
        custom_prompt = self.create_prompt_template(ai_config)

        # 定义一个函数来保存对话上下文
        def save_context(user_input, response):
            try:
                # 将JSON响应转换为字符串
                response_str = str(response)

                memory.save_context(
                    {"content": user_input},
                    {"response": response_str}
                )
                logger.info(f"成功保存对话上下文: {user_input}")
            except Exception as e:
                logger.error(f"保存对话上下文失败: {e}", exc_info=True)

        # 构建并返回链
        chain = RunnableParallel(
            content=RunnablePassthrough(),
            eastern_time=RunnableLambda(lambda _: self.get_eastern_time()),
            chat_history=lambda x: memory.load_memory_variables({}).get("chat_history", []),
            # 添加AI配置参数
            ai_personality=lambda _: ai_config.get("ai_personality",
                                                   self.DEFAULT_AI_CONFIG["ai_personality"]) if ai_config else
            self.DEFAULT_AI_CONFIG["ai_personality"],
            greeting=lambda _: ai_config.get("greeting", self.DEFAULT_AI_CONFIG["greeting"]) if ai_config else
            self.DEFAULT_AI_CONFIG["greeting"],
            relationship_context=lambda _: ai_config.get("relationship_context", self.DEFAULT_AI_CONFIG[
                "relationship_context"]) if ai_config else self.DEFAULT_AI_CONFIG["relationship_context"],
            tone_guidance=lambda _: ai_config.get("tone_guidance",
                                                  self.DEFAULT_AI_CONFIG["tone_guidance"]) if ai_config else
            self.DEFAULT_AI_CONFIG["tone_guidance"],
            response_style=lambda _: ai_config.get("response_style",
                                                   self.DEFAULT_AI_CONFIG["response_style"]) if ai_config else
            self.DEFAULT_AI_CONFIG["response_style"],
            language=lambda _: self.language  # 添加语言参数
        ).assign(
            response=custom_prompt | self.llm | JsonOutputParser()
        )

        # 创建一个包装函数来处理调用和保存上下文
        def invoke_with_memory(inputs):
            # 先加载并打印当前的聊天历史
            current_history = memory.load_memory_variables({}).get("chat_history", [])
            logger.info(f"当前聊天历史条数: {len(current_history)}")

            result = chain.invoke(inputs)

            # 提取用户输入
            user_input = inputs.get("content", "")
            if isinstance(user_input, dict):
                user_input = user_input.get("content", "")

            # 保存上下文
            save_context(user_input, result["response"])

            return result

        return invoke_with_memory

    def _get_chain(self, session_id, ai_config=None):
        """获取或创建对话链，使用缓存提高性能"""
        # 创建缓存键
        config_key = str(ai_config) if ai_config else "default"
        cache_key = f"{session_id}_{config_key}"

        # 检查缓存
        if cache_key not in self._chain_cache:
            self._chain_cache[cache_key] = self.build_chain(session_id, ai_config)

        return self._chain_cache[cache_key]

    def process_input(self, user_input, session_id="default_user", ai_config=None):
        """
        处理用户输入并返回响应

        参数:
            user_input (str): 用户输入的自然语言文本
            session_id (str, 可选): 用户会话ID，用于保持对话上下文
            ai_config (dict或str, 可选): AI配置参数或配置字符串

        返回:
            dict: 包含AI响应和交易信息的字典
        """
        try:
            # 处理配置字符串
            if isinstance(ai_config, str):
                ai_config = self.parse_ai_config_string(ai_config)

            # 获取或创建对话链
            chain_function = self._get_chain(session_id, ai_config)

            # 处理用户输入
            result = chain_function({
                "content": user_input,
                "session_id": session_id
            })

            # 返回不包含聊天历史的结果
            if 'chat_history' in result:
                del result['chat_history']

            return result
        except Exception as e:
            logger.error(f"处理用户输入失败: {e}", exc_info=True)
            # 返回错误信息
            return {
                "error": str(e),
                "content": {
                    "ai_output": "抱歉，处理您的请求时出现了问题。",
                    "random": 50,
                    "emoji": "confused",
                    "transactions": []
                }
            }

    def clear_memory(self, session_id):
        """
        清除指定会话的记忆

        参数:
            session_id (str): 要清除的会话ID
        """
        try:
            # 从缓存中移除
            for key in list(self._chain_cache.keys()):
                if key.startswith(f"{session_id}_"):
                    del self._chain_cache[key]

            # 从Redis中删除
            chat_history = self._create_chat_history(session_id)
            chat_history.clear()
            logger.info(f"已清除会话 {session_id} 的记忆")
            return True
        except Exception as e:
            logger.error(f"清除会话记忆失败: {e}", exc_info=True)
            return False

    def set_prompt_template(self, prompt_template):
        """
        设置新的提示模板

        参数:
            prompt_template (str): 新的提示模板字符串

        返回:
            bool: 是否设置成功
        """
        try:
            if not prompt_template:
                return False

            self.base_prompt_template = prompt_template

            # 清除缓存，强制重新创建链
            self._chain_cache = {}

            return True
        except Exception as e:
            logger.error(f"设置提示模板失败: {e}", exc_info=True)
            return False

    def get_default_prompt_template(self):
        """
        获取默认提示模板

        返回:
            str: 默认提示模板字符串
        """
        return self.DEFAULT_PROMPT_TEMPLATE


# ====== 辅助类 ======
class EnhancedRedisChatMessageHistory(RedisChatMessageHistory):
    """带自动TTL续期的Redis存储"""

    def __init__(self, session_id: str, url: str, ttl: int = 24 * 3600):
        super().__init__(session_id=session_id, url=url)
        self.ttl = ttl

    def add_message(self, message):
        try:
            super().add_message(message)
            # 每次操作后重置TTL
            self.redis_client.expire(self.key, self.ttl)
        except Exception as e:
            logger.error(f"Redis操作失败: {e}")
            # 可以在这里添加备用存储逻辑