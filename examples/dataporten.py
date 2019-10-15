#!/usr/bin/env python3
from pathlib import Path
from typing import Any, Dict

import jinja2
from aiohttp import web
from aiohttp_jinja2 import setup as jinja2_setup, template
from aiohttp_session import SimpleCookieStorage, get_session, setup as session_setup


from aiohttp_oauth2.client.app import oauth2_app
from functools import partial

from aiohttp_oauth2.client.contrib import dataporten


@template("index.html")
async def index(request: web.Request) -> Dict[str, Any]:
    session = await get_session(request)
    return {"user": session.get("user")}


async def logout(request: web.Request):
    session = await get_session(request)
    session.invalidate()
    return web.HTTPTemporaryRedirect(location="/")


async def on_dataporten_login(request: web.Request, dataporten_token):
    session = await get_session(request)
    
    #https://docs.feide.no/developer_oauth/technical_details/oauth_scopes.html?highlight=openid%20userinfo
    async with request.app["session"].get(
        "https://auth.dataporten.no/openid/userinfo",
        headers={"Authorization": f"Bearer {dataporten_token['access_token']}"},
    ) as r:
        session["user"] = await r.json()
        print(session["user"])
    
    #https://docs.feide.no/developer_oauth/technical_details/groups_api.html?highlight=oauth%20authorization
    async with request.app["session"].get(
        "https://groups-api.dataporten.no/groups/me/groups",
        headers={"Authorization": f"Bearer {dataporten_token['access_token']}"},
    ) as r:
        session["groups"] = await r.json()
        print(session["groups"])

    return web.HTTPTemporaryRedirect(location="/")

#make sure to define redirect uri in dataporten dashboard.
FEIDE_CLIENT_ID = 'xxx'
FEIDE_CLIENT_SECRET = 'xyx'

def app_factory() -> web.Application:
    app = web.Application()

    jinja2_setup(
        app, loader=jinja2.FileSystemLoader([Path(__file__).parent / "templates"])
    )
    session_setup(app, SimpleCookieStorage())

    app.add_subapp(
        "/auth/dataporten/",
        dataporten(
            FEIDE_CLIENT_ID,
            FEIDE_CLIENT_SECRET,
            on_login=on_dataporten_login,
            scopes = ['profile', 'userid', 'openid', 'groups', 'peoplesearch', 'email', 'userid-feide'],
            json_data=False,
        ),
    )

    app.add_routes([web.get("/", index), web.get("/auth/logout", logout)])

    return app


if __name__ == "__main__":
    web.run_app(app_factory())
