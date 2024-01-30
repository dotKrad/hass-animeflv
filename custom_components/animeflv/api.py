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

ANIMEFLV_HOST = "https://www3.animeflv.net"

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
        await self.async_logout()
        url = f"{ANIMEFLV_HOST}/auth/sign_in"
        data = {
			"email" : self._username,
			"password" : self._password,
			"remember_me" : "1"
		}

        response = await self.post(url, data)
        if response.status_code != 200:
            raise AnimeFlvApiClientAuthenticationError("Invalid credentials")

        html = response.text
        startProfile = int(html.find("perfil",0, len(html)))

        if(startProfile <= 0): #profile not found
            raise AnimeFlvApiClientAuthenticationError("Invalid credentials")

        endProfile = int(html.find('"', startProfile, len(html)))

        profile = html[startProfile + 7: endProfile]
        self._profile = profile
        return profile

    async def async_logout(self):
        url = f"{ANIMEFLV_HOST}/auth/sign_out";
        response = await self.get(url)
        #if response.status_code == 200:
        #    html = response.text




    async def async_get_data(self) -> any:

        await self.async_login()

        profile = self._profile
        if profile != "":
            url = f"{ANIMEFLV_HOST}/perfil/{profile}/siguiendo?order=updated"

            animes = {}
            response = await self.get(url)
            if response.status_code == 200:
                html = response.text

                soup = BeautifulSoup(html, 'html.parser')

                ul = soup.find('ul', class_='ListAnimes')
                lis = ul.find_all('li')




                for li in lis:
                    img = li.find('img')['src']

                    a = li.find('div', class_="Title").find('strong').find('a')
                    title = a.text.strip()
                    href = a['href']
                    data = {}
                    data['title'] = title
                    data['href'] = f"{ANIMEFLV_HOST}{href}"
                    data['cover'] = f"{ANIMEFLV_HOST}{img}"

                    key = href.replace('/anime/','')

                    animes[key] = data

            today = datetime.datetime.now().strftime("%Y-%m-%d")

            for key in animes.keys():
                anime = animes[key]
                url = anime['href']

                #url = f"https://www3.animeflv.net{href}"
                response = await self.get(url)
                if response.status_code == 200:
                    html = response.text

                    soup = BeautifulSoup(html, 'html.parser')
                    status = soup.find('aside', class_="SidebarA").find('p', class_="AnmStts").find('span').text

                    inEmission = status == 'En emision'

                    jsSentence = "var episodes = "
                    init = html.find(jsSentence, 0)
                    semiColon = html.find(";", init)

                    line = html[init + len(jsSentence) + 1 : semiColon - 1]
                    parts = line.split(",")
                    episodesCount = int(len(parts) / 2)

                    #last episode seen
                    jsSentence = "var last_seen = "
                    init = html.find(jsSentence, 0)
                    semiColon = html.find(";", init)

                    lastSeen = int(html[init + len(jsSentence) : semiColon])

                    #episodeList > li:nth-child(6) > a
                    nextToWatch = None
                    if lastSeen < episodesCount:
                        part = url.split("/")[-1]
                        nextToWatch = ANIMEFLV_HOST + "/ver/" + part + "-" + str(lastSeen + 1)

                    #in emission
                    #var anime_info = ["3423","Dr. Stone: Stone Wars","dr-stone-stone-wars","2021-01-28"];

                    nextEpisode = None
                    if inEmission:
                        jsSentence = "var anime_info = "
                        init = html.find(jsSentence, 0)
                        semiColon = html.find(";", init)

                        line = html[init + len(jsSentence) + 1 : semiColon - 1]
                        parts = line.split(',"')
                        if len(parts) >= 4:
                            nextEpisode = parts[3].replace('"','')


                    #description
                    #body > div.Wrapper > div > div > div.Container > div > main > section:nth-child(1) > div.Description > p
                    description = soup.find('div', class_="Description").find('p').text

                    anime['lastSeen'] = lastSeen
                    anime['episodesCount'] = episodesCount
                    anime['inEmission'] = inEmission
                    anime['nextEpisode'] = nextEpisode
                    anime['progress'] = round(lastSeen / episodesCount * 100, 2)
                    anime['today'] = nextEpisode == today
                    anime["nextToWatch"] = nextToWatch
                    anime["description"] = description

        self._animes = animes
        await self.async_logout()
        return animes

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
