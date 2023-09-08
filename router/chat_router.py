from http import HTTPStatus

from service.chat import Chat
from model.chat import Message
from model.custom_http import Response
from model.exceptions import ClientNotFoundError, InvalidMessageError


class ChatRouter:
    def __init__(self):
        self.chat = Chat()

    async def connect(self, request, reader, writer):
        await self.chat.client_connected(request, reader, writer)

    async def send_private(self, request):
        msg = Message.from_dict(request.json)
        if not msg.to_username or not msg.from_username:
            return Response(HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST.phrase, body="to_username and from_username are required")

        try:
            msg.is_private = True
            await self.chat.send_private_message(msg)
        except (ClientNotFoundError, InvalidMessageError) as e:
            return Response(HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST.phrase, body=e)

        return Response(HTTPStatus.OK, HTTPStatus.OK.phrase)

    async def send_all(self, request):
        msg = Message.from_dict(request.json)
        if not msg.from_username:
            return Response(HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST.phrase, body="from_username is required")

        try:
            await self.chat.broadcast(msg)
        except InvalidMessageError as e:
            return Response(HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST.phrase, body=e)

        return Response(HTTPStatus.OK, HTTPStatus.OK.phrase)

    async def get_status(self):
        return Response(HTTPStatus.OK, HTTPStatus.OK.phrase, headers=None, body=await self.chat.get_status())