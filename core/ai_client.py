
import json
import time
from datetime import datetime, timezone
from pathlib import Path

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

        # AI 调用统计文件
        self.usage_log_path = (
            Path(__file__).resolve().parent.parent
            / "logs"
            / "ai_usage.jsonl"
        )

    def _record_usage(
        self,
        stage,
        response,
        success,
        duration_ms,
    ):
        """将 AI 调用统计追加写入 JSONL 文件"""

        usage = getattr(response, "usage", None) if response else None

        record = {
            "stage": stage or "unspecified",
            "model": self.model,
            "prompt_tokens": (
                usage.prompt_tokens if usage else None
            ),
            "completion_tokens": (
                usage.completion_tokens if usage else None
            ),
            "total_tokens": (
                usage.total_tokens if usage else None
            ),
            "success": success,
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        try:
            self.usage_log_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with self.usage_log_path.open(
                "a",
                encoding="utf-8",
            ) as file:
                file.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    ) + "\n"
                )

        except Exception as e:
            # 统计记录失败不能影响原有 AI 业务调用
            print(f"AI 使用统计写入失败：{e}")

    def chat(
        self,
        system_prompt,
        user_prompt,
        stage="unspecified",
    ):
        """普通文本调用"""

        start_time = time.perf_counter()
        response = None
        success = False

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                stream=False,
                extra_body={
                    "thinking": {"type": "disabled"}
                },
            )

            if not response.choices:
                raise ValueError("AI 未返回任何结果")

            content = response.choices[0].message.content

            if not content or not content.strip():
                raise ValueError("AI 返回了空文本")

            success = True
            return content

        finally:
            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            self._record_usage(
                stage=stage,
                response=response,
                success=success,
                duration_ms=duration_ms,
            )

    def chat_json(
        self,
        system_prompt,
        user_prompt,
        stage="unspecified",
    ):
        """JSON 格式调用，包含输出完整性和格式校验"""

        start_time = time.perf_counter()
        response = None
        success = False

        try:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    response_format={
                        "type": "json_object"
                    },
                    max_tokens=32000,
                    stream=False,
                    extra_body={
                        "thinking": {"type": "disabled"}
                    },
                )

            except Exception as e:
                raise RuntimeError(
                    f"AI 接口调用失败：{str(e)}"
                ) from e

            # 检查响应
            if not response.choices:
                raise ValueError("AI 未返回任何结果")

            choice = response.choices[0]
            message = choice.message

            # 检查结束原因
            finish_reason = choice.finish_reason

            if finish_reason == "length":
                raise ValueError(
                    "AI 输出达到最大 Token 限制，"
                    "返回内容可能被截断。"
                    "请减少需求内容或调整输出 Token 限制。"
                )

            if finish_reason == "content_filter":
                raise ValueError(
                    "AI 返回内容触发了内容过滤，无法完成需求分析。"
                )

            if response.usage:
                print("\n========== AI Token 使用情况 ==========")
                print(
                    "Prompt Tokens：",
                    response.usage.prompt_tokens,
                )
                print(
                    "Completion Tokens：",
                    response.usage.completion_tokens,
                )
                print(
                    "Total Tokens：",
                    response.usage.total_tokens,
                )
                print("Finish Reason：", finish_reason)
                print("========================================\n")

            # 检查拒绝响应
            if getattr(message, "refusal", None):
                raise ValueError(
                    f"AI 拒绝生成内容：{message.refusal}"
                )

            content = message.content

            if not content or not content.strip():
                raise ValueError("AI 返回了空 JSON 内容")

            # JSON 格式校验
            try:
                parsed_result = json.loads(content)

            except json.JSONDecodeError as e:
                start = max(0, e.pos - 200)
                end = min(len(content), e.pos + 200)

                error_context = repr(content[start:end])

                print("\n========== AI JSON 解析失败 ==========")
                print("模型：", self.model)
                print("返回长度：", len(content))
                print("结束原因：", finish_reason)
                print("错误位置：", e.pos)
                print("错误信息：", str(e))
                print("错误附近内容：", error_context)
                print("======================================\n")

                raise ValueError(
                    f"AI 返回的 JSON 格式不合法：{e.msg}；"
                    f"位置：{e.pos}；"
                    f"返回长度：{len(content)}。"
                    "请检查终端中的错误详情。"
                ) from e

            # 必须是 JSON 对象
            if not isinstance(parsed_result, dict):
                raise ValueError(
                    "AI 返回的 JSON 顶层结构必须是对象"
                )

            success = True
            return content

        finally:
            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            self._record_usage(
                stage=stage,
                response=response,
                success=success,
                duration_ms=duration_ms,
            )


# 全局统一客户端
ai_client = AIClient()
