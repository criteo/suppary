# Supparize

A CLI tool to fetch and summarize your Slack threads.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package installer
- Slack Bot Token with the following scopes:
  - `channels:history`
  - `channels:read`
  - `groups:read`
  - `im:read`
  - `mpim:read`

## Installation

Using uv:

```sh
uv sync
```


## Configuration

Set your Slack Bot token as an environment variable:

```bash
export SLACK_TOKEN="xoxb-your-token"
```

## Basic usage - fetch threads from multiple channels

```bash
uv run supparize general announcements
```

## Specify end date

```bash
uv run supparize general --end-date 2024-03-20
```

## Customize lookup duration

```bash
uv run supparize general --duration 14
```

## Combine options

```bash
uv run supparize general announcements --end-date 2024-03-20 --duration 14
```
