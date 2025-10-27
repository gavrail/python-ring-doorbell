"""Test module which runs the first example in the README."""

import asyncio
import getpass
import json
from pathlib import Path
from pprint import pprint

from ring_doorbell import Auth, AuthenticationError, Requires2FAError, Ring, RingEventListener

user_agent = "YourProjectName-1.0"  # Change this
cache_file = Path(user_agent + ".token.cache")


def token_updated(token) -> None:
    cache_file.write_text(json.dumps(token))


def otp_callback():
    return input("2FA code: ")


async def do_auth():
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    auth = Auth(user_agent, None, token_updated)
    try:
        await auth.async_fetch_token(username, password)
    except Requires2FAError:
        await auth.async_fetch_token(username, password, otp_callback())
    return auth




class SnapShotter(object):

    def __init__(self, doorbell):
        self.doorbell = doorbell

    def on_event(self, event):
        if event.kind == "motion":
            print("Motion detected!", event)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.doorbell.async_get_snapshot(filename="snapshot.jpg"))

async def main() -> None:
    if cache_file.is_file():  # auth token is cached
        auth = Auth(user_agent, json.loads(cache_file.read_text()), token_updated)
        ring = Ring(auth)
        try:
            await ring.async_create_session()  # auth token still valid
        except AuthenticationError:  # auth token has expired
            auth = await do_auth()
    else:
        auth = await do_auth()  # Get new auth token
        ring = Ring(auth)

    await ring.async_update_data()

    listener = RingEventListener(ring)

    await listener.start()

    devices = ring.devices()
    doorbell = devices['doorbots'][0]
    snap_shotter = SnapShotter(doorbell)
    listener.add_notification_callback(snap_shotter.on_event)

    await asyncio.Event().wait()

    await auth.async_close()


if __name__ == "__main__":
    asyncio.run(main())
