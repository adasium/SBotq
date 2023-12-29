from client import Client
from getenv import getenv


def main() -> int:
    client = Client()
    client.run(getenv('TOKEN'))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
