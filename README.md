# \#MugiWait

A discord bot to send [r/anime commentfaces][r/anime] ([original source][r/anime github])

## How to run

(Requires Python >= 3.6)

[Create the Discord application][discordapp] and get its token

Generate the invite link. Select:

- Scope: bot
- Bot permissions: manage webhooks, read messages/view channels, send messages, manage messages

Add the application to your server

Clone the repository and cd into it

Create a `.env` file containing `TOKEN={{your Discord application token}}` (without the braces)

`pip install -r requirements.txt`

`python src\mugiwait.py`

Additional options:

- `-l` select the log directory (default: `logs`)
- `-d` run with additional logging (debug)
- `-i` send Imgur links instead of uploading image files (use the links in `src/resources/commentfaces.py`)
- `-g` send Github links instead of uploading image files (use the same assets as [r/anime][r/anime github])

Note: Imgur/Github links will not display if the user disable link previews.

## How to use

Mugi reacts to messages with two formats:

- `#commentface {{optional: text after}}`
- `[{{optional: text before}}](#commentface {{optional: text after}})`

e.g.  
`#anko this is nice`  
`[](#whisperwhisper this is a secret)`

Mugi will not react to:

- Messages outside of text channels (threads are also excluded)
- Messages not starting with `#` or `[`
- Messages formatted incorrectly
- Incorrect commentface code

[r/anime]: https://old.reddit.com/r/anime/wiki/commentfaces
[r/anime github]: https://github.com/r-anime/comment-face-assets
[discordapp]: https://discord.com/developers/applications/
