"""Scrape footy wire website to get afl stats data for the 2025 season"""

import re
from typing import List, Tuple

import httpx
from logger import logger

from bs4 import BeautifulSoup
from nanoid import generate

from dtos.player_profile_dto import PlayerProfileDTO
from helpers import TEAM_SLUG_MAP, name_corrections


class FootyWireScraper():
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(headers=
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            timeout=30.0
        )

    async def get_player_profile_stats(
        self,
        display_name: str,
        team_name: str,
        dob: str
    ) -> PlayerProfileDTO | None:
        """Scrape url to get profile related stats (height, weight etc.) for a given player

        Args:
            display_name (str): Name of player as displayed on the AflTables site
            team_name (str): Team the player plays for

        Returns:
            PlayerProfileDTO: DTO containing player profile related data
        """
        team_name_split = team_name.split()
        if len(team_name_split) > 1:
            team_name = "-".join(team_name_split)
        
        player_name = self._convert_display_name(display_name)
        url = f"{self.base_url}/pp-{TEAM_SLUG_MAP[team_name]}--{player_name.lower()}"
        response = await self.client.get(url)
        
        if response.status_code != httpx.codes.OK:
            logger.error(f"Failed to fetch player profile for {display_name} from footy wire. Status code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        if "Oops! Player Not Found ..." in soup.get_text(strip=True):
            logger.warning(f"Can't find {player_name} in FootyWire")
            logger.info(f"Tried scraping the following url: {url}")
            return
        
        profile_str = soup.find("div", id="playerProfileData1").get_text(strip=True)
        origin = self._extract_identity_data(profile_str)     

        biometrics_str = soup.find("div", id="playerProfileData2").get_text(strip=True)
        height, weight, position = self._scrape_biometric_data(biometrics_str)

        return PlayerProfileDTO(
            player_id=generate(size=10),
            display_name=display_name,
            dob=dob,
            height=height,
            weight=weight,
            position=position,
            origin=origin
        )
    
    def _convert_display_name(self, name: str) -> str:
        """Convert display name into name format used by footy wire

        Args:
            name (str): display name of a given player

        Raises:
            ValueError: Confirms a player has at least a first and second name 

        Returns:
            str: Returns a string in the format {first_name}-{other_name(s)}
        """
        #TODO: Create a mapping for names containing '
        # Split the name into "Last" and "First [Middle]"

        res = re.split(r"[,'\s]", name)
        res.remove("")
        if len(res) < 2:
            raise ValueError("Name must be in 'Last, First' format")
        res.insert(0, res.pop())

        if name_corrections.get(res[-1]):
            corrected_name = self.correct_last_name(res[-1])
            res.pop() # this might on
            return "-".join(res + corrected_name)

        # Reassemble in First-Middle-Last format
        return "-".join(res)
    
    def correct_last_name(self, last_name: str) -> List[str]:
        return name_corrections.get(last_name, [last_name])

    def _extract_identity_data(self, input_str: str) -> Tuple[str, str]:
        """Use a regex to extract certain data about a specific player

        Args:
            input_str (str): Html element as a string

        Returns:
            Tuple[str, str]: Return the dob and origin of a player
        """
        # dob_match = re.search(r'Born:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', input_str)
        origin_match = re.search(r'Origin:\s+(.+)', input_str)

        # dob = dob_match.group(1) if dob_match else None
        origin = origin_match.group(1).strip() if origin_match else None

        return origin
    
    def _scrape_biometric_data(self, input_str: str) -> Tuple[int, int, str]:
        """Extract biometric data from a string using a regex expression

        Args:
            input_str (str): String where the data is to be extracted from

        Returns:
            Tuple[int, int, str]: Return height, weight and positions of the given player
        """
        height_match = re.search(r'Height:\s*(\d+)\s*cm', input_str)
        weight_match = re.search(r'Weight:\s*(\d+)\s*kg', input_str)

        height = int(height_match.group(1)) if height_match else None
        weight = int(weight_match.group(1)) if weight_match else None
        
        position_section = re.search(r'Position:\s*(.*)', input_str, re.DOTALL)
        
        if position_section:
            raw_positions = position_section.group(1)
            positions = [pos.strip() for pos in raw_positions.replace("\n", "").split(",")]
            position_str = ", ".join(positions)
        else:
            position_str = None

        return height, weight, position_str     


if __name__ == "__main__":
    scraper = FootyWireScraper(base_url="https://www.footywire.com/afl/footy")
    #TODO: use the following for unit tests
    player_profile_dto = scraper.get_player_profile_stats("draper, sid", "adelaide")
    player_profile_dto = scraper.get_player_profile_stats("de koning, tom", "carlton")
    player_profile_dto = scraper.get_player_profile_stats("OConnell, liam", "st kilda")
