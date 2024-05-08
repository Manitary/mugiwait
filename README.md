# \#MugiWait

A discord bot to send [r/anime commentfaces][r/anime] ([original source][r/anime github])

## How to run

[Create the Discord application][discordapp] and get its token after enabling `Message Content Intent`.

Generate the invite link. Select:

- Scope: bot
- Bot permissions: manage webhooks, read messages/view channels, send messages, manage messages, read message history

Add the application to your server

### Running it natively

Clone the repository and cd into it

Grab the submodules:

- first time: `git submodule update --init --recursive --remote`
- thereafter: `git submodule update --recursive --remote`

Create a `.env` file containing `TOKEN={{your Discord application token}}` (without the braces) - see .env.template for an example

Install python (currently requiring 3.12) (a nice way to do so is `pyenv`)

Install poetry

Install the required modules: `poetry install`

Run the bot: `poetry run python3 src/mugiwait.py`

Additional options:

- `-l` select the log directory (default: `logs`)
- `-d` run with additional logging (debug)
- `-i` send Imgur links instead of uploading image files (use the links in `src/resources/commentfaces.py`)
- `-g` send Github links instead of uploading image files (use the same assets as [r/anime][r/anime github])

Note: Imgur/Github links will not display for users who disabled link previews.

Warning: Imgur links are not up to date. While the functionality exists, it may be considered deprecated.

### Running it via Docker

Clone the repository and cd into it

Create a `.env` file containing `TOKEN={{your Discord application token}}` (without the braces) - see .env.template for an example

If you wanna have finer control you can do this:
```sh
# calling Docker directly
docker build -t mass_mentioner:v0.2.0 .
docker run -d --rm mass_mentioner:v0.2.0
```

You could also use the Docker Compose solution:
```sh
# using docker-compose
docker-compose up -d
```

## How to use (via message)

Mugi reacts to messages with two formats:

- `#commentface {{optional: text after}}`
- `[{{optional: text before}}](#commentface {{optional: text after}})`

and supports the use of spoiler tags.

e.g.  
`#anko this is nice`  
`[](#whisperwhisper this is a secret)`  
`||[this will be spoiler-tagged](#nosenpai "including the commentface itself")||`

Mugi will not react to:

- Messages outside of text channels
- Messages not starting with `#`, `[`, or `||`
- Messages formatted incorrectly
- Incorrect commentface code

Webhooks cannot "reply" to messages, i.e. have a reference to an existing message in the channel. However, Mugi can mimic the behaviour by adding a short quote (i.e. text preceded by `>`) that includes the author of the message, a link to the message, and a short excerpt of the message.

## How to use (via slash command)

Type `/mugi` to bring up the command.

The first parameter is the commentface code; it comes with an autocomplete suggestion box, making mugi easier to use as one does not need to know all commentface codes to a tee.

The second parameter is optional, and can include any additional text to send together with the commentface.

Mugi will notify you (and only you) if you submit an incorrect commentface code.

[r/anime]: https://old.reddit.com/r/anime/wiki/commentfaces
[r/anime github]: https://github.com/r-anime/comment-face-assets
[discordapp]: https://discord.com/developers/applications/
