import logging
from asyncio.streams import StreamReader, StreamWriter
import re
from model.custom_http import Request

PRIVATE_MSG_PATTERN = re.compile(r"^@(\w+)")


class Client:
    def __init__(self, username, writer):
        self.username = username
        self.writer = writer


class Message:
    def __init__(self, username, data):
        self.username = username
        self.data = data


class Chat:
    def __init__(self):
        self.clients = {}
        self.messages = []

    async def client_connected(self, req: Request, reader: StreamReader, writer: StreamWriter):
        address = writer.get_extra_info('peername')
        logging.info('Client connected: %s', address)

        username = req.json['username']
        client = Client(
                username=username, writer=writer
            )
        self.clients[username] = client

        writer.write("Connected to the chat.\n".encode())
        await writer.drain()

        await self.load_history(client)

        while True:
            data = (await reader.read(1024)).decode()
            if not data or data == r"\quit":
                del self.clients[username]
                writer.write("Disconnected from the chat.\n".encode())
                await writer.drain()
                break

            msg = Message(
                username=username, data=data
            )
            if is_private := re.search(PRIVATE_MSG_PATTERN, data):
                await self.send_private_message(
                    to_username=is_private.group(1),
                    msg=msg,
                    from_writer=writer
                )
            else:
                self.messages.append(msg)
                await self.broadcast(msg)

        logging.info('Stop serving %s', address)
        writer.close()

    async def broadcast(self, msg: Message):
        for _, client in self.clients.items():
            if msg.username == client.username:
                continue
            client.writer.write(f"{msg.username}: {msg.data}".encode())
            await client.writer.drain()

    async def send_private_message(self, to_username: str, msg: Message, from_writer: StreamWriter):
        try:
            client = self.clients[to_username]
        except KeyError as e:
            logging.warning("User not found: " + str(e))
            from_writer.write(f"User {to_username} not found.\n".encode())
            await from_writer.drain()
        else:
            client.writer.write(f"{msg.username}: {msg.data}".encode())
            await client.writer.drain()

    async def get_status(self):
        return f"Connected clients: {len(self.clients)}, messages: {len(self.messages)}"

    async def load_history(self, client: Client):
        if not self.messages:
            client.writer.write(f"Chat history empty. Write something!\n".encode())
            await client.writer.drain()

        for msg in self.messages[:50]:
            if msg.username == client.username:
                username = 'You'
            else:
                username = msg.username

            client.writer.write(f"{username}: {msg.data}\n".encode())
        await client.writer.drain()
