import json
import os
import select
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PROTOCOL_VERSION = "2024-11-05"


def load_env_file() -> None:
    candidates = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class TavilyMCPError(RuntimeError):
    pass


class TavilyMCPClient:
    def __init__(
        self,
        *,
        command: list[str] | None = None,
        api_key: str | None = None,
        protocol_version: str = DEFAULT_PROTOCOL_VERSION,
        read_timeout: float = 15.0,
    ) -> None:
        load_env_file()
        self.command = command or ["npx", "-y", "tavily-mcp@0.1.3"]
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.protocol_version = protocol_version
        self.read_timeout = read_timeout
        if not self.api_key:
            raise TavilyMCPError("Missing TAVILY_API_KEY environment variable for Tavily MCP.")
        self._process: subprocess.Popen[bytes] | None = None
        self._request_id = 0

    def __enter__(self) -> "TavilyMCPClient":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def start(self) -> None:
        if self._process is not None:
            return
        env = {**os.environ, "TAVILY_API_KEY": self.api_key}
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self._initialize()

    def close(self) -> None:
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.kill()
        finally:
            self._process = None

    def _read_message(self) -> dict[str, Any]:
        if self._process is None or self._process.stdout is None:
            raise TavilyMCPError("Tavily MCP process is not running.")

        headers: dict[str, str] = {}
        while True:
            ready, _, _ = select.select([self._process.stdout], [], [], self.read_timeout)
            if not ready:
                raise TavilyMCPError("Timed out waiting for Tavily MCP response headers.")
            line = self._process.stdout.readline()
            if not line:
                stderr = b""
                if self._process.stderr is not None:
                    try:
                        stderr = self._process.stderr.read1(4096)
                    except Exception:
                        stderr = b""
                raise TavilyMCPError(
                    "Tavily MCP connection closed unexpectedly."
                    + (f" stderr={stderr.decode('utf-8', 'replace')}" if stderr else "")
                )
            if line == b"\r\n":
                break
            decoded = line.decode("utf-8", "replace").strip()
            if ":" in decoded:
                key, value = decoded.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        try:
            length = int(headers["content-length"])
        except KeyError as exc:
            raise TavilyMCPError(f"Missing Content-Length header in Tavily MCP response: {headers}") from exc

        ready, _, _ = select.select([self._process.stdout], [], [], self.read_timeout)
        if not ready:
            raise TavilyMCPError("Timed out waiting for Tavily MCP response body.")
        payload = self._process.stdout.read(length)
        return json.loads(payload.decode("utf-8"))

    def _send_message(self, message: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise TavilyMCPError("Tavily MCP process is not running.")
        body = json.dumps(message).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        self._process.stdin.write(header + body)
        self._process.stdin.flush()

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._request_id += 1
        request_id = self._request_id
        self._send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        while True:
            message = self._read_message()
            if "id" not in message:
                continue
            if message["id"] != request_id:
                continue
            if "error" in message:
                raise TavilyMCPError(f"Tavily MCP error on {method}: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise TavilyMCPError(f"Unexpected Tavily MCP result for {method}: {message}")
            return result

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send_message(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
            }
        )

    def _initialize(self) -> None:
        self._request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "policy-localization-agent", "version": "0.1.0"},
            },
        )
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._request("tools/list", {})
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise TavilyMCPError(f"Unexpected tools/list response: {result}")
        return [tool for tool in tools if isinstance(tool, dict)]

    def _resolve_search_tool_name(self) -> str:
        candidate_names = ("tavily-search", "tavily_search", "search")
        tools = self.list_tools()
        names = {str(tool.get("name", "")) for tool in tools}
        for candidate in candidate_names:
            if candidate in names:
                return candidate
        raise TavilyMCPError(f"Could not find a Tavily search tool. Available tools: {sorted(names)}")

    def search(
        self,
        query: str,
        *,
        topic: str = "general",
        max_results: int = 5,
        search_depth: str = "advanced",
        include_raw_content: bool = False,
        include_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": include_raw_content,
        }
        if include_domains:
            arguments["include_domains"] = include_domains
        tool_name = self._resolve_search_tool_name()
        result = self._request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text = item["text"].strip()
                    if text.startswith("{"):
                        return json.loads(text)
        if "structuredContent" in result and isinstance(result["structuredContent"], dict):
            return result["structuredContent"]
        raise TavilyMCPError(f"Unexpected Tavily MCP tools/call response: {result}")
