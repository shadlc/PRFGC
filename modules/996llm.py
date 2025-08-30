"""LLM模块"""

import json
import http.client
from urllib.parse import urlparse
from typing import Dict, List, AsyncGenerator, Generator, Union

import aiohttp

from src.utils import Module

class LLM(Module):
    """LLM模块"""

    ID = "LLM"
    NAME = "LLM模块"
    HELP = {} # 本模块目前主要为内部其他模块和功能提供LLM接入能力
    CONFIG = "llm.json"
    GLOBAL_CONFIG = {
        "providers": [],
        "models": [],
    }
    CONV_CONFIG = None
    AUTO_INIT = True

    def __init__(self, event, auth=0):
        super().__init__(event, auth)
        self.session = None
        if "LLM" not in self.robot.func:
            self.robot.func["llm_chat"] = self.llm_chat
            self.robot.func["async_llm_chat"] = self.async_llm_chat

    def premise(self):
        return False

    async def __aexit__(self, exc_type, exc_value, traceback):
        """异步上下文管理器退出时关闭资源"""
        await self.close()

    def _build_model_map(self) -> Dict[str, Dict]:
        """构建模型名称到配置的映射"""
        model_map = {}
        for model in self.config["models"]:
            provider = next(
                (p for p in self.config["providers"] if p["name"] == model["provider"]),
                None
            )
            if provider:
                model_map[model["name"]] = {
                    "model_identifier": model["model_identifier"],
                    "provider_config": provider
                }
        return model_map

    def _get_request_params(self, model_name: str | None = None) -> Dict:
        """获取请求参数"""
        model_map = self._build_model_map()
        if len(model_map) == 0:
            raise ValueError("未找到任何可用模型!")
        if model_name:
            if model_name not in model_map:
                raise ValueError(f"未找到模型[{model_name}]对应的配置!")
            model_info = model_map[model_name]
        else:
            model_info = next(iter(model_map.values()))
        provider = model_info["provider_config"]

        return {
            "model": model_info["model_identifier"],
            "base_url": provider["base_url"],
            "api_key": provider["api_key"],
            "max_retry": provider.get("max_retry", 2),
            "timeout": provider.get("timeout", 30),
            "retry_interval": provider.get("retry_interval", 10)
        }

    def _make_sync_request(self, messages: List[Dict], params: Dict, stream: bool = False) -> Union[Dict, Generator]:
        """同步API请求核心逻辑"""
        parsed_url = urlparse(params["base_url"])
        is_https = parsed_url.scheme == "https"

        conn_class = http.client.HTTPSConnection if is_https else http.client.HTTPConnection
        conn = conn_class(parsed_url.netloc, timeout=params["timeout"])

        # 准备请求头和数据
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {params['api_key']}",
            "Accept": "text/event-stream" if stream else "application/json"
        }

        body = {
            "model": params["model"],
            "messages": messages,
            "stream": stream
        }

        conn.request("POST", "/v1/chat/completions", body=json.dumps(body), headers=headers)
        response = conn.getresponse()

        if response.status != 200:
            raise http.client.HTTPException(f"API请求失败: {response.status} {response.reason}")

        if stream:
            return self._handle_stream_response(response)
        else:
            return json.loads(response.read().decode())

    def _handle_stream_response(self, response: http.client.HTTPResponse) -> Generator:
        """处理流式响应"""
        buffer = b""
        while True:
            chunk = response.read(1024)
            if not chunk:
                break
            buffer += chunk

            while b'\n\n' in buffer:
                event, buffer = buffer.split(b'\n\n', 1)
                if event.startswith(b"data: "):
                    data = event[6:].decode().strip()
                    if data == "[DONE]":
                        return
                    try:
                        item = json.loads(data)
                        yield item.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    except json.JSONDecodeError:
                        continue

    async def _make_async_request(self, messages: List[Dict], params: Dict, stream: bool = False) -> Union[Dict, AsyncGenerator]:
        """异步API请求核心逻辑"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {params['api_key']}",
            "Accept": "text/event-stream" if stream else "application/json"
        }

        body = {
            "model": params["model"],
            "messages": messages,
            "stream": stream
        }

        async with self.session.post(
            f"{params['base_url']}/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=params["timeout"]
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise http.client.HTTPException(f"API请求失败: {response.status} {error}")

            if stream:
                return self._handle_async_stream(response)
            else:
                return await response.json()

    async def _handle_async_stream(self, response: aiohttp.ClientResponse) -> AsyncGenerator:
        """处理异步流式响应"""
        buffer = b""
        async for chunk in response.content.iter_any():
            buffer += chunk
            while b'\n\n' in buffer:
                event, buffer = buffer.split(b'\n\n', 1)
                if event.startswith(b"data: "):
                    data = event[6:].decode().strip()
                    if data == "[DONE]":
                        return
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

    def llm_chat(
        self,
        msg: str,
        model_name: str = None,
        stream: bool = False
    ) -> Union[Dict, Generator]:
        """同步生成文本"""
        messages: List[Dict] = [{"role": "user", "content": msg}]
        system_prompt = self.config["system_prompt"]
        if system_prompt:
            messages = [{"role": "system", "content": self.config["system_prompt"]}, *messages]
        params = self._get_request_params(model_name)
        return self._make_sync_request(messages, params, stream)

    async def async_llm_chat(
        self,
        msg: str,
        model_name: str = None,
        stream: bool = False
    ) -> Union[Dict, AsyncGenerator]:
        """异步生成文本"""
        messages: List[Dict] = [{"role": "user", "content": msg}]
        system_prompt = self.config["system_prompt"]
        if system_prompt:
            messages = [{"role": "system", "content": self.config["system_prompt"]}, *messages]
        params = self._get_request_params(model_name)
        return await self._make_async_request(messages, params, stream)

    async def close(self):
        """异步关闭资源"""
        if self.session:
            await self.session.close()
            self.session = None
