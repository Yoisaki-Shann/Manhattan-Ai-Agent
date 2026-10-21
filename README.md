# Manhattan AI Agent

Manhattan is an AI-powered Discord bot for Uma Musume circles. It answers questions about player profiles and circle statistics using an OpenAI-compatible language model and the API from [uma.moe](https://uma.moe).

> **Note:** This project is currently under active development. Features may change or break without notice.

## Features

- Look up player profiles, total fans, active days, ranks, and recent statistics.
- View circle information and fan-gain leaderboards.
- Check how many fans a linked player earned today.
- Link Discord users to Uma Musume player accounts.
- Set a default circle for a Discord server.
- Use recent conversation context to handle follow-up questions.

## Development

This project was developed with assistance from AI tools, including Claude and GPT-Luna.

## Project structure

```text
.
├── api/
│   └── apiwarpper.py       # Umamoe API client and response cache
├── bot/
│   ├── agent.py            # LLM conversation and tool-calling loop
│   └── discord_client.py   # Discord events and bot commands
├── data/
│   └── manhattan.db        # Local SQLite database
├── db/
│   └── database.py         # SQLite setup and account/server settings
├── tools/
│   ├── registry.py         # LLM tool definitions and handlers
│   └── stats.py            # Player and circle statistics
├── config.py               # Environment-based configuration
├── main.py                 # Application entry point
└── requirements.txt        # Python dependencies
```

## Disclaimer

This project is an unofficial fan-made tool created for educational and community management purposes. It is not affiliated with Cygames, Inc. or the Uma Musume Pretty Derby franchise. All relevant copyrights and trademarks belong to their respective owners.
