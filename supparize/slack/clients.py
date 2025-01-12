import asyncio
from datetime import datetime, timedelta
from typing import List

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient
import click


class SlackClient:
    def __init__(self, token: str):
        self.client = AsyncWebClient(token=token)

    async def get_channel_messages(
        self, channel_name: str, end_date: datetime, duration: int
    ) -> List[dict]:
        # Set end_date to end of day
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        try:
            # Get channel ID from name
            result = await self.client.conversations_list()
            channel = None

            if result["ok"]:
                for ch in result["channels"]:
                    if ch["name"] == channel_name:
                        channel = ch["id"]
                        break

                if not channel:
                    click.echo(f"Channel not found: {channel_name}", err=True)
                    return []
            else:
                click.echo(
                    f"Error fetching channel list: {result.get('error', 'Unknown error')}",
                    err=True,
                )
                return []

            # Proceed with message fetching using channel ID
            start_date = end_date - timedelta(days=duration)
            messages = []

            async def fetch_history(cursor: str | None = None) -> dict:
                return await self.client.conversations_history(
                    channel=channel,
                    oldest=start_date.timestamp(),
                    latest=end_date.timestamp(),
                    cursor=cursor,
                )

            async def fetch_thread_replies(thread_ts: str) -> List[dict]:
                try:
                    result = await self.client.conversations_replies(
                        channel=channel,
                        ts=thread_ts,
                    )
                    if result["ok"]:
                        return result["messages"]
                    else:
                        click.echo(
                            f"Error fetching thread replies in {channel_name}: {result.get('error', 'Unknown error')}",
                            err=True,
                        )
                        return []
                except SlackApiError as e:
                    click.echo(
                        f"Error fetching thread replies in {channel_name}: {str(e)}",
                        err=True,
                    )
                    return []

            # Get channel history
            result = await fetch_history()

            if result["ok"]:
                messages.extend(result["messages"])

                # Handle pagination
                while result.get("has_more", False):
                    result = await fetch_history(
                        result["response_metadata"]["next_cursor"]
                    )
                    if result["ok"]:
                        messages.extend(result["messages"])
                        click.echo(
                            f"Fetched {len(messages)} messages from channel {channel_name}"
                        )
                    else:
                        click.echo(
                            f"Error in pagination for channel {channel_name}: {result.get('error', 'Unknown error')}",
                            err=True,
                        )

                # Fetch thread replies for messages that have them
                thread_tasks = []
                for message in messages:
                    if message.get("thread_ts") and message.get("reply_count", 0) > 0:
                        task = asyncio.create_task(
                            fetch_thread_replies(message["thread_ts"])
                        )
                        thread_tasks.append(task)

                if thread_tasks:
                    thread_replies = await asyncio.gather(
                        *thread_tasks, return_exceptions=True
                    )
                    for replies in thread_replies:
                        if isinstance(replies, list):
                            messages.extend(replies[1:])  # Skip the parent message

            else:
                click.echo(
                    f"Error fetching messages from channel {channel_name}: {result.get('error', 'Unknown error')}",
                    err=True,
                )

        except SlackApiError as e:
            click.echo(f"Error processing channel {channel_name}: {str(e)}", err=True)
            return []

        return messages
