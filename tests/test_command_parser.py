from commands import parse_pipe

def test_parse_pipe():
    message = '!addcmd payank ```!echo :uwat: | !shrug | !shrug | !shrug | !shrug```'
    pipe = parse_pipe(message, prefix='!')
    assert pipe, [
        [
            Command(
                name='addcmd', raw_args='payank !echo :uwat: | !shrug | !shrug | !shrug | !shrug',
                args=['payank', '!echo', ':uwat:', '|', '!shrug', '|', '!shrug', '|', '!shrug', '|', '!shrug'],
            ),
        ],
    ]
