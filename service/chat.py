import logging
import traceback
from asyncio.streams import StreamReader, StreamWriter
from copy import copy

from model.chat import Client, Message, QUIT_CODE
from model.custom_http import Request
from model.exceptions import (
    ClientNotFoundError,
    InvalidMessageError,
    MultipleSessionsError,
)


class Chat:
    def __init__(self):
        self.clients = {}
        self.messages = []

    async def client_connected(
        self, req: Request, reader: StreamReader, writer: StreamWriter
    ):
        username = None
        try:
            address = writer.get_extra_info("peername")
            logging.info("Client connected: %s", address)

            username = req.json()["username"]
            client = Client(username=username, writer=writer)

            if self.clients.get(username):
                raise MultipleSessionsError
            self.clients[username] = client

            writer.write(
                Message(
                    data="Connected to the chat.", is_system=True
                ).to_bytes()
            )
            await writer.drain()

            await self.load_history(client)

            await self.start_message_handler(reader, writer)

        except MultipleSessionsError:
            writer.write(
                Message(
                    data="Cannot provide multiple sessions for user.",
                    is_system=True,
                    is_error=True,
                ).to_bytes()
            )
        except Exception:
            logging.error(traceback.print_exc())
            writer.write(
                Message(
                    data="Unexpected error.", is_system=True, is_error=True
                ).to_bytes()
            )

        finally:
            if username and username in self.clients:
                del self.clients[username]
            writer.write(
                Message(
                    data="Disconnected from the chat.", is_system=True
                ).to_bytes()
            )
            await writer.drain()

            logging.info("Stop serving %s", address)
            writer.close()

    async def broadcast(self, msg: Message):
        for _, client in self.clients.items():
            if msg.from_username == client.username:
                continue
            client.writer.write(msg.to_bytes())
            await client.writer.drain()

    async def send_private_message(self, msg: Message):
        try:
            client = self.clients[msg.to_username]
        except KeyError as e:
            raise ClientNotFoundError from e
        else:
            client.writer.write(msg.to_bytes())
            await client.writer.drain()

    async def get_status(self):
        return f"Connected clients: {len(self.clients)}, messages: {len(self.messages)}"

    async def load_history(self, client: Client):
        if not self.messages:
            client.writer.write(
                Message(
                    data="Chat history empty. Write something!",
                    is_system=True,
                ).to_bytes()
            )
            await client.writer.drain()

        for msg in self.messages[:50]:
            if msg.from_username == client.username:
                msg = copy(msg)
                msg.from_username = "You"
            client.writer.write(msg.to_bytes())
        await client.writer.drain()

    async def start_message_handler(
        self, reader: StreamReader, writer: StreamWriter
    ):
        while True:
            if not (data := await reader.read(1024)):
                break

            try:
                msg = Message.from_bytes(data)
            except InvalidMessageError as e:
                writer.write(
                    Message(
                        data=str(e), is_system=True, is_error=True
                    ).to_bytes()
                )
                await writer.drain()
                continue

            if msg.is_system and int(msg.data) == QUIT_CODE:
                break

            if msg.is_private:
                try:
                    await self.send_private_message(msg)
                except ClientNotFoundError as e:
                    logging.warning("User not found: " + str(e))
                    writer.write(
                        Message(
                            data=f"User {msg.to_username} not found.",
                            is_system=True,
                            is_error=True,
                        ).to_bytes()
                    )
                    await writer.drain()
            else:
                self.messages.append(msg)
                await self.broadcast(msg)
