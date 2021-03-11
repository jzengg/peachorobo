# Peachorobo
A discord bot that helps you schedule secret santa style pairings for mystery dinners.

## Setup
Create a virtualenv after cloning the repo and install requirements into it
```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Supply environment variables
Place a `.env` file with these environment variables and dotenv will pick it up.
```
DISCORD_TOKEN - should be the token that corresponds to the bot you set up in Discord applications
DISCORD_MYSTERY_DINNER_CHANNEL_ID - ID of the channel you want the bot to be active in
CALENDAR_EMAILS - comma separated list of emails that will be invited to  Google Calendar event
DB_JSON_PATH - path to the json file used for the 'DB'
```


When first running, you will need to grant access to your Google
Calendar using oauth which uses the information from `credentials.json`. 
Once you grant permission, the token information is persisted to `token.pickle`

## Start bot in tmux session named discordbot
```
tmux new -s discordbot
python3 peachorobo/main.py
```

### tmux cheatsheet
```
C-b d # Detach from a session
tmux ls # See running sessions
tmux attach -t <SESSION_NAME> # Reattach to a session
```
