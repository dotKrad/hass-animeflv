"""Sample API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout

import datetime
import cloudscraper
from bs4 import BeautifulSoup


class AnimeFlvApiClientError(Exception):
    """Exception to indicate a general API error."""


class AnimeFlvApiClientCommunicationError(
    AnimeFlvApiClientError
):
    """Exception to indicate a communication error."""


class AnimeFlvApiClientAuthenticationError(
    AnimeFlvApiClientError
):
    """Exception to indicate an authentication error."""


ANIMEFLV_HOST = "https://www4.animeflv.net"


class AnimeFlvApiClient:
    """Sample API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        hass
    ) -> None:
        """Sample API Client."""
        self._username = username
        self._password = password
        self._hass = hass
        self._session = None
        self._profile = None
        self._animes = {}

    async def _getSession(self) -> any:
        if self._session is None:

            self._session = await self._hass.async_add_executor_job(cloudscraper.create_scraper,
                                                                    {
                                                                        'browser': 'firefox',
                                                                        'platform': 'android',
                                                                        # 'mobile': False
                                                                        'desktop': False
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
        await self.async_logout()
        # https://www4.animeflv.net/auth/sign_in
        url = f"{ANIMEFLV_HOST}/auth/sign_in"
        data = {
            "email": self._username,
            "password": self._password,
            "remember_me": "1"
        }

        response = await self.post(url, data)
        if response.status_code != 200:
            raise AnimeFlvApiClientAuthenticationError("Invalid credentials")

        html = response.text
        startProfile = int(html.find("perfil", 0, len(html)))

        if (startProfile <= 0):  # profile not found
            raise AnimeFlvApiClientAuthenticationError("Invalid credentials")

        endProfile = int(html.find('"', startProfile, len(html)))

        profile = html[startProfile + 7: endProfile]
        self._profile = profile
        return profile

    async def async_logout(self):
        url = f"{ANIMEFLV_HOST}/auth/sign_out"
        response = await self.get(url)
        # if response.status_code == 200:
        #    html = response.text

    async def async_get_data(self) -> any:

        await self.async_login()
        try:
            profile = self._profile
            animes = {}

            page = 1
            totalPages = 0
            if profile != "":
                while totalPages == 0 or page <= totalPages:
                    url = f"{ANIMEFLV_HOST}/perfil/{profile}/siguiendo?order=title&page={page}"
                    response = await self.get(url)
                    if response.status_code != 200:
                        totalPages = -1
                        break

                    html = response.text

                    soup = BeautifulSoup(html, 'html.parser')
                    if totalPages == 0:
                        # read if more pages
                        pagination = soup.find('ul', class_='pagination')
                        if pagination is not None:
                            pagesLi = pagination.find_all('li')
                            totalPages = max(len(pagesLi) - 2, 1)
                        else:
                            totalPages = 1

                    page += 1
                    ul = soup.find('ul', class_='ListAnimes')
                    if ul is None:
                        continue

                    lis = ul.find_all('li')

                    for li in lis:
                        img_tag = li.find('img')
                        title_div = li.find('div', class_="Title")
                        strong_tag = title_div.find(
                            'strong') if title_div else None
                        a = strong_tag.find('a') if strong_tag else None
                        if img_tag is None or a is None:
                            continue

                        img = img_tag.get('src')
                        href = a.get('href')
                        if not img or not href:
                            continue

                        title = a.text.strip()
                        data = {}
                        data['title'] = title
                        data['href'] = f"{ANIMEFLV_HOST}{href}"
                        data['cover'] = f"{ANIMEFLV_HOST}{img}"

                        key = href.replace('/anime/', '')

                        animes[key] = data

                today = datetime.datetime.now().strftime("%Y-%m-%d")

                for key in animes.keys():
                    anime = animes[key]
                    url = anime['href']

                    # url = f"https://www3.animeflv.net{href}"
                    response = await self.get(url)
                    if response.status_code == 200:
                        html = response.text

                        soup = BeautifulSoup(html, 'html.parser')
                        sidebar = soup.find('aside', class_="SidebarA")
                        status_p = sidebar.find(
                            'p', class_="AnmStts") if sidebar else None
                        status_span = status_p.find(
                            'span') if status_p else None
                        if status_span is None:
                            continue

                        status = status_span.text

                        inEmission = status == 'En emision'

                        jsSentence = "var episodes = "
                        init = html.find(jsSentence, 0)
                        if init < 0:
                            continue
                        semiColon = html.find(";", init)
                        if semiColon < 0:
                            continue

                        line = html[init + len(jsSentence) + 1: semiColon - 1]
                        parts = line.split(",")
                        episodesCount = int(len(parts) / 2)

                        # last episode seen
                        jsSentence = "var last_seen = "
                        init = html.find(jsSentence, 0)
                        if init < 0:
                            continue
                        semiColon = html.find(";", init)
                        if semiColon < 0:
                            continue

                        try:
                            lastSeen = int(
                                html[init + len(jsSentence): semiColon])
                        except ValueError:
                            continue

                        # episodeList > li:nth-child(6) > a
                        nextToWatch = None
                        if lastSeen < episodesCount:
                            part = url.split("/")[-1]
                            nextToWatch = ANIMEFLV_HOST + "/ver/" + \
                                part + "-" + str(lastSeen + 1)

                        # in emission
                        # var anime_info = ["3423","Dr. Stone: Stone Wars","dr-stone-stone-wars","2021-01-28"];

                        nextEpisode = None
                        if inEmission:
                            jsSentence = "var anime_info = "
                            init = html.find(jsSentence, 0)
                            if init >= 0:
                                semiColon = html.find(";", init)
                                if semiColon >= 0:
                                    line = html[init +
                                                len(jsSentence) + 1: semiColon - 1]
                                    parts = line.split(',"')
                                    if len(parts) >= 4:
                                        nextEpisode = parts[3].replace('"', '')

                        # description
                        # body > div.Wrapper > div > div > div.Container > div > main > section:nth-child(1) > div.Description > p
                        description_div = soup.find(
                            'div', class_="Description")
                        description_p = description_div.find(
                            'p') if description_div else None
                        description = description_p.text if description_p else ""

                        anime['lastSeen'] = lastSeen
                        anime['episodesCount'] = episodesCount
                        anime['inEmission'] = inEmission
                        anime['nextEpisode'] = nextEpisode
                        anime['progress'] = round(
                            lastSeen / episodesCount * 100, 2) if episodesCount > 0 else 0
                        anime['today'] = nextEpisode == today
                        anime["nextToWatch"] = nextToWatch
                        anime["description"] = description

            self._animes = animes
            return animes
        finally:
            await self.async_logout()

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
                    raise AnimeFlvApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.json()

        except asyncio.TimeoutError as exception:
            raise AnimeFlvApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise AnimeFlvApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise AnimeFlvApiClientError(
                "Something really wrong happened!"
            ) from exception
