from client import Client
from getenv import getenv


async def main():
    client = Client()
    client.loop.create_task(
        client.start(
            getenv('TOKEN'),
            bot=True,
        ),
    )

if __name__ == '__main__':
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.create_task(main())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
