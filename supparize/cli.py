import os
import click
from datetime import datetime
from slack_sdk.web.async_client import AsyncWebClient
import asyncio

from .slack.clients import SlackClient
from .slack.services import organize_messages_by_thread


@click.command()
@click.argument("channels", nargs=-1, required=True)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: datetime.now().strftime("%Y-%m-%d"),
    help="End date for message retrieval (YYYY-MM-DD)",
)
@click.option(
    "--duration", type=int, default=7, help="Number of days to look back from end date"
)
def summarize(channels: list[str], end_date: datetime, duration: int):
    """Fetch Slack threads from specified channels."""

    # Get environment variables
    slack_token = os.getenv("SLACK_TOKEN")
    if not slack_token:
        raise click.ClickException("SLACK_TOKEN environment variable is required")

    client = SlackClient(token=slack_token)

    # Fetch messages from all channels asynchronously
    all_messages = []

    async def fetch_messages():
        tasks = []
        for channel in channels:
            task = asyncio.create_task(
                client.get_channel_messages(channel, end_date, duration)
            )
            tasks.append((task, channel))

        for task, channel in tasks:
            try:
                messages = await task
                all_messages.extend(messages)
                click.echo(f"Retrieved {len(messages)} messages from channel {channel}")
            except Exception as e:
                click.echo(f"Error processing channel {channel}: {str(e)}", err=True)

    asyncio.run(fetch_messages())

    # Organize messages by thread
    organized_messages = organize_messages_by_thread(all_messages)

    # Output results
    click.echo("\nMessages organized by thread:")
    for thread_ts in sorted(organized_messages.keys(), key=float):
        thread = organized_messages[thread_ts]
        thread_date = datetime.fromtimestamp(float(thread_ts)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        click.echo(f"Thread from {thread_date}: {len(thread)} messages")

    return organized_messages


if __name__ == "__main__":
    summarize()
