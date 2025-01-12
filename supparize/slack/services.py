from typing import Dict, List
from datetime import datetime


def organize_messages_by_thread(messages: List[dict]) -> Dict[str, List[dict]]:
    organized_threads = {}

    for message in messages:
        # Get thread_ts (will be None for non-threaded messages)
        thread_ts = message.get("thread_ts") or message.get("ts")

        if thread_ts not in organized_threads:
            organized_threads[thread_ts] = []

        organized_threads[thread_ts].append(message)

    # Sort messages in each thread by timestamp
    for thread_ts in organized_threads:
        organized_threads[thread_ts].sort(key=lambda x: float(x["ts"]))

    return organized_threads
