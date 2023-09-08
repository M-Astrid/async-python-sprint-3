import asyncio
import json
import re
import sys
import argparse

import colorama
import httpx
from colorama import Fore, Style

from model.chat import Message
from model.custom_http import Request


PRIVATE_MSG_PATTERN = re.compile(r"^@(\w+)")


class Client:
    async def connect(self, host: str, port: int, username: str):
        data = json.dumps({'username': username})
        req = Request('POST', '/connect', 'HTTP/1.1', {
            'Host': f'{host}:{port}'
        }, data)

        reader, writer = await asyncio.open_connection(host, port)
        writer.write(req.to_text().encode())
        await writer.drain()
        return reader, writer

    async def start_chatting(self, host: str, port: int):
        colorama.init()
        print(Fore.YELLOW, end="")
        print("Welcome to the messenger!")
        print("If you want to quit, enter 'quit'")
        print("Enter your username: " + Style.RESET_ALL)

        username = sys.stdin.readline().strip()

        reader, writer = await self.connect(host, port, username)
        receive_task = asyncio.create_task(self._receive_messages(reader))
        send_task = asyncio.create_task(self._send_messages(writer, username))

        await asyncio.gather(receive_task, send_task)

    @staticmethod
    async def _receive_messages(reader):
        while True:
            data = await reader.readline()
            message = Message.from_bytes(data)
            if message.is_private:
                print(Fore.RED + "[private] ", end="")
            if message.is_system:
                print(Fore.YELLOW, end="")
            print((f"{message.from_username}: " if message.from_username else "") + message.data.strip() + Style.RESET_ALL)

    @staticmethod
    async def _send_messages(writer, from_username):
        while True:
            data = (await asyncio.get_running_loop().run_in_executor(None, sys.stdin.readline)).strip()
            if not data:
                continue

            is_private = re.search(PRIVATE_MSG_PATTERN, data)
            to_username = is_private.group(1) if is_private else None

            msg = Message(from_username=from_username, to_username=to_username, data=data, is_private=bool(is_private))

            writer.write(msg.to_bytes())
            await writer.drain()


if __name__ == '__main__':
    COMMANDS = ['connect', 'send_private', 'send_all', 'status']

    parser = argparse.ArgumentParser(description='Chat client')
    parser.add_argument('--server-url', dest='server',
                        help='chat server address in format <host>:<port>', required=True, metavar='<host>:<port>')
    parser.add_argument('command', metavar='command', type=str,
                        help=f'a command to execute {COMMANDS}', choices=COMMANDS)

    parser.add_argument('--from_username', dest='from_username',
                        help='enter your name', metavar='<your_name>', required=bool({'send_all', 'send_private'} & set(sys.argv)))

    parser.add_argument('--to_username', dest='to_username',
                        help='enter target user name', metavar='<user_name>', required='send_private' in sys.argv)

    parser.add_argument('--message', dest='message',
                        help='enter message', metavar='<message_text>', required=bool({'send_all', 'send_private'} & set(sys.argv)))

    args = parser.parse_args()
    host, port = args.server.split(":")

    match args.command:
        case 'connect':
            asyncio.run(Client().start_chatting(host, int(port)))
        case 'send_private':
            msg = Message(from_username=args.from_username, to_username=args.to_username, data=args.message, is_private=True)
            resp = httpx.post(f'http://{host}:{port}/send-private', json=msg.to_dict())
            print(resp.status_code, resp.text if resp.text else '')
        case 'send_all':
            msg = Message(from_username=args.from_username, to_username=None, data=args.message)
            resp = httpx.post(f'http://{host}:{port}/send-all', json=msg.to_dict())
            print(resp.status_code, resp.text if resp.text else '')
        case 'status':
            resp = httpx.get(f'http://{host}:{port}/status')
            print(resp.text)
