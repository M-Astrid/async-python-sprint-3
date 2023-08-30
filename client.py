import asyncio
import sys

async def receive_messages(reader):
    while True:
        data = await reader.readline()
        message = data.decode().strip()
        print(message)

async def send_messages(writer):
    while True:
        message = await asyncio.get_running_loop().run_in_executor(None, sys.stdin.readline)
        writer.write(message.encode())
        await writer.drain()

async def start_client():
    reader, writer = await asyncio.open_connection('127.0.0.1', 8000)

    print("If you want to quit, enter 'quit'")
    print("Enter your username: ",)

    msg = await asyncio.get_running_loop().run_in_executor(None, sys.stdin.readline)
    writer.write(msg.encode())
    await writer.drain()

    receive_task = asyncio.create_task(receive_messages(reader))
    send_task = asyncio.create_task(send_messages(writer))

    await asyncio.gather(receive_task, send_task)

asyncio.run(start_client())