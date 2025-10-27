"""Test module which runs the first example in the README."""

import asyncio
import getpass
import json
from pathlib import Path
from pprint import pprint

from ring_doorbell import Auth, AuthenticationError, Requires2FAError, Ring

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

    devices = ring.devices()
    doorbell = devices['doorbots'][0]
    try:
        await doorbell.async_recording_download(
            (await doorbell.async_history(limit=100, kind='ding'))[0]['id'],
                            filename='last_ding.mp4',
                            override=True)
    finally:
        await auth.async_close()


if __name__ == "__main__":
    asyncio.run(main())
