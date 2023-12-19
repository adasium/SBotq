# SBotq

Discord chat bot that works for [SB](<https://en.wikipedia.org/wiki/Ministry_of_Public_Security_(Poland)>) ![monkaS](https://cdn.betterttv.net/emote/56e9f494fff3cc5c35e5287e/1x)


## env

specify in env variables or in .env file inside project root

| Key                                | Value                                                  |
|------------------------------------|--------------------------------------------------------|
| `TOKEN`                            | discord authentication token                           |
| `INSPIRATIONAL_MESSAGE_CHANNEL_ID` | channel id that should get daily inspirational message |
| `MARKOV_CHANNEL_BLACKLIST`         | bot cannot eavesdrop here (separator=`;`)              |
| `RANDOM_MARKOV_MESSAGE_CHANNEL_ID` | channel id that should get random markov message       |

## how to run

works for python3.8 so newer versions should work too

```bash
virtualenv -p python3.8 .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python main.py
```

# development

```bash
virtualenv -p python3.8 .venv
source .venv/bin/activate
pip3 install -r requirements.txt
pip3 install -r requirements.dev.txt
pre-commit install
python main.py
```

# credits

https://github.com/tsoding/kgbotka/

https://github.com/Ciremun/discord-selfbot
