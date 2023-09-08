from asyncio import StreamReader
from email.parser import Parser
from urllib.parse import urlparse, parse_qs
from http import HTTPMethod
import json

from model.exceptions import BadRequestException

MAX_LINE = 64 * 1024
MAX_HEADERS = 100


def headers_to_text(headers: dict):
    return "\r\n".join([k + ":" + v for k, v in headers.items()])


class Request:
    def __init__(self, method: str, target: str, ver: str, headers: dict, body: str | None):
        self.method = method
        self.target = target
        self.ver = ver
        self.headers = headers
        self.body = body
        headers["Content-Length"] = str(len(f"{body}\r\n\r\n".encode()))

    @property
    def path(self):
        return self.url.path

    @property
    def query(self):
        return parse_qs(self.url.query)

    @property
    def url(self):
        return urlparse(self.target)

    def json(self):
        return json.loads(self.body)

    def to_text(self):
        return f"{self.method} {self.target} {self.ver}\r\n{headers_to_text(self.headers)}\r\n\r\n{self.body}\r\n\r\n"

    @classmethod
    async def from_stream(cls, reader: StreamReader):
        req_line = str((await reader.readline()), "iso-8859-1")
        req_line = req_line.rstrip("\r\n")
        words = req_line.split()
        if len(words) != 3:
            raise BadRequestException("Malformed request line")

        method, target, ver = words

        if ver != "HTTP/1.1":
            raise BadRequestException("Unexpected HTTP version")

        headers = await cls.parse_headers(reader)

        content_length = headers.get("Content-Length")

        if not content_length or method in [
            HTTPMethod.GET,
            HTTPMethod.HEAD,
            HTTPMethod.DELETE,
            HTTPMethod.OPTIONS,
            HTTPMethod.TRACE,
        ]:
            body = b""
        else:
            body = await cls.parse_body(reader, int(content_length))

        return Request(method, target, ver, headers, body)

    @staticmethod
    async def parse_headers(reader: StreamReader):
        headers = []
        while True:
            line = await reader.readline()
            if len(line) > MAX_LINE:
                raise BadRequestException("Header line is too long")

            if line in (b"\r\n", b"\n", b""):
                break

            headers.append(line)
            if len(headers) > MAX_HEADERS:
                raise BadRequestException("Too many headers")

        sheaders = b"".join(headers).decode("iso-8859-1")

        return Parser().parsestr(sheaders)

    @staticmethod
    async def parse_body(reader: StreamReader, content_length: int):
        if content_length > MAX_LINE:
            raise BadRequestException("Content length is too big")

        textb = await reader.readexactly(content_length)
        return textb.decode("iso-8859-1")


class Response:
    def __init__(self, status: int, reason: str, headers: dict | None = None, body: str | None = None):
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body

    def to_text(self):
        return (
            f"HTTP/1.1 {self.status} {self.reason}\r\n{headers_to_text(self.headers) if self.headers else ''}\r\n\r\n"
            + (f"{self.body}\r\n\r\n" if self.body else "")
        )
