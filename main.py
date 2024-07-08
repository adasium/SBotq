import settings
from client import Client


def main() -> int:
    client = Client()
    client.run(settings.TOKEN)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
