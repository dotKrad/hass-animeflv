"""Sample API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout

import cloudscraper


class AnimeFlvApiClientError(Exception):
    """Exception to indicate a general API error."""


class IntegrationBlueprintApiClientCommunicationError(
    AnimeFlvApiClientError
):
    """Exception to indicate a communication error."""


class IntegrationBlueprintApiClientAuthenticationError(
    AnimeFlvApiClientError
):
    """Exception to indicate an authentication error."""

ANIMEFLV_HOST = "https://www3.animeflv.net"

class IntegrationBlueprintApiClient:
    """Sample API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        hass,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._username = username
        self._password = password
        self._hass = hass
        self._session = None
        self._profile = None


    async def _getSession(self) -> any:
        if self._session is None:

            self._session = await self._hass.async_add_executor_job(cloudscraper.create_scraper,
                {
                        'browser': 'firefox',
                        'platform': 'android',
                        #'mobile': False
                        'desktop' : False
                }
            )

        return self._session

    async def post(self, url, data) -> any:
        session = await self._getSession()
        response = await self._hass.async_add_executor_job(session.post, url, data)
        return response

    async def get(self, url) -> any:
        session = await self._getSession()
        response = await self._hass.async_add_executor_job(session.get, url)
        return response

    async def async_login(self) -> any:
        session = await self._getSession()
        url = f"{ANIMEFLV_HOST}/auth/sign_in"
        data = {
			"email" : self._username,
			"password" : self._password,
			"remember_me" : "1"
		}

        response = await self.post(url, data)
        if response.status_code != 200:
            raise IntegrationBlueprintApiClientAuthenticationError("Invalid credentials")

        html = response.text
        startProfile = int(html.find("perfil",0, len(html)))

        if(startProfile <= 0): #profile not found
            raise IntegrationBlueprintApiClientAuthenticationError("Invalid credentials")

        endProfile = int(html.find('"', startProfile, len(html)))

        profile = html[startProfile + 7: endProfile]
        self._profile = profile
        print(profile)
        return profile




    async def async_get_data(self) -> any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="get", url="https://jsonplaceholder.typicode.com/posts/1"
        )

    async def async_set_title(self, value: str) -> any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="patch",
            url="https://jsonplaceholder.typicode.com/posts/1",
            data={"title": value},
            headers={"Content-type": "application/json; charset=UTF-8"},
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                if response.status in (401, 403):
                    raise IntegrationBlueprintApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.json()

        except asyncio.TimeoutError as exception:
            raise IntegrationBlueprintApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise IntegrationBlueprintApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise AnimeFlvApiClientError(
                "Something really wrong happened!"
            ) from exception
