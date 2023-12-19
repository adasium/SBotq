from client import Client
from getenv import getenv


def main():
    client = Client()
    client.run(
        getenv('TOKEN'),
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
