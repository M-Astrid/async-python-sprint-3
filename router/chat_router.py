from http import HTTPStatus

from service.chat import Chat
from model.chat import Message
from model.custom_http import Response
from model.exceptions import ClientNotFoundError


class ChatRouter:
    def __init__(self):
        self.chat = Chat()

    async def connect(self, request, reader, writer):
        await self.chat.client_connected(request, reader, writer)

    async def send_private(self, request):
        msg = Message.from_dict(request.json)
        try:
            await self.chat.send_private_message(msg)
        except ClientNotFoundError as e:
            return Response(HTTPStatus.NOT_FOUND, HTTPStatus.NOT_FOUND.phrase, body=e)
        return Response(HTTPStatus.OK, HTTPStatus.OK.phrase)

    async def send_all(self, request):
        msg = Message.from_dict(request.json)
        await self.chat.broadcast(msg)
        return Response(HTTPStatus.OK, HTTPStatus.OK.phrase)

    async def get_status(self):
        return Response(HTTPStatus.OK, HTTPStatus.OK.phrase, headers=None, body=await self.chat.get_status())