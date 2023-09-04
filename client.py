import asyncio
import json
import sys
import argparse

import httpx

from model.custom_http import Request


class Client:
    async def start_chatting(self, host: str, port: int):

        print("Welcome to the messenger!")
        print("If you want to quit, enter 'quit'")
        print("Enter your username: ",)
        username = sys.stdin.readline().strip()

        req = Request('POST', '/connect', 'HTTP/1.1', {
            'Host': f'{host}:{port}',
        }, json.dumps({'username': username}))

        reader, writer = await asyncio.open_connection(host, port)
        writer.write(req.to_text().encode())
        await writer.drain()

        receive_task = asyncio.create_task(self._receive_messages(reader))
        send_task = asyncio.create_task(self._send_messages(writer))

        await asyncio.gather(receive_task, send_task)

    @staticmethod
    async def _receive_messages(reader):
        while True:
            data = await reader.readline()
            message = data.decode().strip()
            print(message)

    @staticmethod
    async def _send_messages(writer):
        while True:
            message = await asyncio.get_running_loop().run_in_executor(None, sys.stdin.readline)
            writer.write(message.encode())
            await writer.drain()


if __name__ == '__main__':
    COMMANDS = ['connect', 'send_private', 'send_all', 'status']

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--server-url', dest='server',
                        help='chat server address in format <host>:<port>', required=True, metavar='<host>:<port>')
    parser.add_argument('command', metavar='command', type=str,
                        help=f'a command to execute {COMMANDS}', choices=COMMANDS)

    parser.add_argument('--from_username', dest='from_username',
                        help='enter your name', metavar='<your_name>')

    parser.add_argument('--to_username', dest='to_username',
                        help='enter target user name', metavar='<user_name>')

    args = parser.parse_args()
    host, port = args.server.split(":")

    match args.command:
        case 'connect':
            asyncio.run(Client().start_chatting(host, int(port)))
        case 'send_private':
            httpx.post(f'http://{host}:{port}/send-private', json={'msg': sys.stdin.readline().strip(), 'to_username': args.to_username, 'from_username': args.from_username}, timeout=60)
        case 'send_all':
            httpx.post(f'http://{host}:{port}/send-all', json={'msg': sys.stdin.readline().strip(), 'from_username': args.from_username}, timeout=60)
        case 'status':
            resp = httpx.get(f'http://{host}:{port}/status')
            print(resp.text)
