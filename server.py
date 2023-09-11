import asyncio
import logging
import traceback
from asyncio import StreamReader, StreamWriter
from http import HTTPStatus

from model.exceptions import BadRequestException, NotFoundException
from model.custom_http import Request, Response
from router.chat_router import ChatRouter
from utils import logging_config


logging_config.setup_logger()


class HttpServer:
    def __init__(self, host: str, port: int, server_name: str):
        self._host = host
        self._port = port
        self._server_name = server_name
        self.chat_router = ChatRouter()

    async def router(
        self, request: Request, reader: StreamReader, writer: StreamWriter
    ) -> Response | None:
        match (request.method, request.path):
            case ("POST", "/connect"):
                return await self.chat_router.connect(request, reader, writer)

            case ("POST", "/send-private"):
                return await self.chat_router.send_private(request)

            case ("POST", "/send-all"):
                return await self.chat_router.send_all(request)

            case ("GET", "/status"):
                return await self.chat_router.get_status()

        return Response(HTTPStatus.NOT_FOUND, HTTPStatus.NOT_FOUND.phrase)

    async def client_connected(
        self, reader: StreamReader, writer: StreamWriter
    ):
        address = writer.get_extra_info("peername")
        logging.info("Request from: %s", address)

        try:
            req = await Request.from_stream(reader)
            logging.info(req.to_text())
            await self.validate_request(req)
            resp = await self.router(req, reader, writer)
        except NotFoundException as e:
            resp = Response(
                HTTPStatus.NOT_FOUND, HTTPStatus.NOT_FOUND.phrase, body=e
            )
        except BadRequestException as e:
            logging.error(traceback.print_exc())
            resp = Response(
                HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST.phrase, body=e
            )
        except Exception:
            logging.error(traceback.print_exc())
            resp = Response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                HTTPStatus.INTERNAL_SERVER_ERROR.phrase,
            )

        if resp:
            logging.info(resp.to_text())
            writer.write(resp.to_text().encode())
            await writer.drain()

        logging.info("Closed connection %s", address)
        writer.close()

    async def validate_request(self, req: Request):
        host = req.headers.get("Host")
        if not host:
            raise BadRequestException("Bad request")
        if host not in (
            self._server_name,
            f"{self._server_name}:{self._port}",
            f"{self._host}:{self._port}",
        ):
            raise NotFoundException("Not found")

    async def run(self):
        logging.info(f"Serving at {self._host}:{self._port}")

        srv = await asyncio.start_server(
            self.client_connected, self._host, self._port
        )

        async with srv:
            await srv.serve_forever()


if __name__ == "__main__":
    server = HttpServer("127.0.0.1", 8001, "chat.local")
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logging.info("Server stopped")
