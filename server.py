import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Client:
    def __init__(self, username, writer):
        self.username = username
        self.writer = writer


class Message:
    def __init__(self, username, data):
        self.username = username
        self.data = data


class Server:
    def __init__(self):
        self.clients = []
        self.messages = []

    async def client_connected(self, reader: StreamReader, writer: StreamWriter):
        address = writer.get_extra_info('peername')
        logger.info('Client connected: %s', address)

        username = (await reader.read(1024)).decode().strip()
        client = Client(
                username=username, writer=writer
            )

        self.clients.append(
            client
        )
        writer.write(f"Welcome to the messenger, {username}! \n".encode())
        await writer.drain()

        while True:
            data = (await reader.read(1024)).decode()
            if data == 'quit':
                self.clients.remove(client)
                writer.write("Disconnected from the chat.\n".encode())
                await writer.drain()
                break

            msg = Message(
                username=username, data=data
            )
            await self.broadcast(msg)

        logger.info('Stop serving %s', address)
        writer.close()

    async def broadcast(self, msg: Message):
        for client in self.clients:
            if msg.username == client.username:
                continue
            client.writer.write(f"{msg.username}: {msg.data}".encode())
            await client.writer.drain()


    async def run(self, host: str, port: int):
        print(f"Serving at {host}:{port}")
        srv = await asyncio.start_server(
            self.client_connected, host, port)

        async with srv:
            await srv.serve_forever()


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.run('127.0.0.1', 8000))