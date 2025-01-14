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
            channel = await self._get_channel_id(channel_name)
            if not channel:
                return []

            # Proceed with message fetching using channel ID
            start_date = end_date - timedelta(days=duration)
            messages = []

            # Get channel history
            result = await self._fetch_history(channel, start_date, end_date)

            if result["ok"]:
                messages.extend(result["messages"])

                # Handle pagination
                while result.get("has_more", False):
                    result = await self._fetch_history(
                        channel,
                        start_date,
                        end_date,
                        result["response_metadata"]["next_cursor"],
                    )
                    if result["ok"]:
                        messages.extend(result["messages"])
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
                            self._fetch_thread_replies(
                                channel, channel_name, message["thread_ts"]
                            )
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

    async def _get_channel_id(self, channel_name: str) -> str | None:
        """Get channel ID from channel name.

        Args:
            channel_name: Name of the channel to look up

        Returns:
            Channel ID if found, None otherwise
        """

        # Try to find channel in different conversation types
        for conv_type in ["public_channel", "private_channel", "mpim,im"]:
            try:
                result = await self._fetch_conversations(conv_type)

                while True:
                    if not result["ok"]:
                        click.echo(
                            f"Error fetching {conv_type} list: {result.get('error', 'Unknown error')}",
                            err=True,
                        )
                        break

                    # Check channels in current page
                    for ch in result["channels"]:
                        if (
                            ch.get("name") == channel_name
                            or ch.get("user") == channel_name
                        ):
                            return ch["id"]

                    # Check if there are more pages
                    if not result.get("response_metadata", {}).get("next_cursor"):
                        break

                    # Fetch next page
                    result = await self._fetch_conversations(
                        conv_type, result["response_metadata"]["next_cursor"]
                    )

            except SlackApiError as e:
                click.echo(f"Error fetching {conv_type} list: {str(e)}", err=True)

        click.echo(f"Channel not found: {channel_name}", err=True)
        return None

    async def _fetch_thread_replies(
        self, channel: str, channel_name: str, thread_ts: str
    ) -> List[dict]:
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

    async def _fetch_history(
        self,
        channel: str,
        start_date: datetime,
        end_date: datetime,
        cursor: str | None = None,
    ) -> dict:
        return await self.client.conversations_history(
            channel=channel,
            oldest=start_date.timestamp(),
            latest=end_date.timestamp(),
            cursor=cursor,
        )

    async def _fetch_conversations(
        self, conv_type: str, cursor: str | None = None
    ) -> dict:
        return await self.client.conversations_list(
            types=conv_type,
            cursor=cursor,
            limit=1000,  # Maximum allowed by Slack API
        )
