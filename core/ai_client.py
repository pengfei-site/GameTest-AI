
import json
from openai import OpenAI

from config.settings import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    validate_ai_config,
)


class AIClient:
    """GameTest AI 统一大模型调用客户端"""

    def __init__(self):
        validate_ai_config()

        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=120.0,
            max_retries=2,
        )

        self.model = DEEPSEEK_MODEL

    def chat(self, system_prompt, user_prompt):
        """普通文本调用"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            extra_body={
                "thinking": {"type": "disabled"}
            },
        )

        return response.choices[0].message.content

    def chat_json(self, system_prompt, user_prompt):
        """JSON 格式调用"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_object"
            },
            max_tokens=4000,
            stream=False,
            extra_body={
                "thinking": {"type": "disabled"}
            },
        )

        content = response.choices[0].message.content

        if not content or not content.strip():
            raise ValueError("AI 返回了空 JSON 内容")

        # 检查返回内容是否为合法 JSON
        json.loads(content)

        return content


ai_client = AIClient()
