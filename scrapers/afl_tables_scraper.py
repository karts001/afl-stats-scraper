import asyncio
import re
from urllib.parse import urljoin
from collections import defaultdict
from logger import logger

from typing import List, Tuple
import httpx
from bs4 import BeautifulSoup, ResultSet

from dtos.games_dto import GameDTO, MatchMetadataDTO, MatchScoreDTO, ReducedGameDTO
from dtos.player_profile_dto import PlayerProfileDTO
from dtos.stats_dto import PlayerMatchStatsDTO
from helpers import FINALS_ROUND_MAP, before_second_dot, convert_date_format, field_names
from scrapers.footy_wire_scraper import FootyWireScraper
from services.game_service import GameService
from services.player_service import PlayerService
from services.stat_service import StatService


class AflTablesScraper():
    def __init__(
        self,
        player_service: PlayerService,
        game_service: GameService,
        stat_service: StatService,
        base_url: str,
        footy_wire_scraper: FootyWireScraper,
    ):
        self.player_service = player_service
        self.game_service = game_service
        self.stat_service = stat_service
        self.footy_wire_scraper = footy_wire_scraper
        self.base_url = base_url
        self.game_index_counter = defaultdict(int)
        self.player_tracker: set[Tuple[str, str]] = set()
        self.scraped_players: set[PlayerProfileDTO] = set()
        self.scraped_stats: set[PlayerMatchStatsDTO] = set()
        self.scraped_games: set[GameDTO] = set()
        self._player_lock = asyncio.Lock()
        self.client = httpx.AsyncClient(headers=
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            timeout=30.0
        )
        self.dob_cache: dict[str, str] = {}


    async def get_match_links(self, year: int = 2025) -> List[str]:
        """Get a list of endpoints which refer to specific match stats for a given year

        Args:
            year (int, optional): Year of data to scrape. Defaults to 2025.

        Returns:
            List[str]: A list of endpoints which correspond to matches which have occured
            in that year.
        """
        logger.info("Getting a list of endpoints which refer to stats from specific games")
        response = await self.client.get(f"{self.base_url}{year}t.html")

        if response.status_code == httpx.codes.OK:
            soup = BeautifulSoup(response.text, "html.parser")
            all_links = soup.find_all("a", href=True)

            return list(dict.fromkeys(
                link["href"] for link in all_links if f"games/{year}" in link["href"]
            ))
        else:
            logger.error(f"❌ Failed to fetch match links for {year}. Status: {response.status_code}")
            logger.info(f"Response content: {response.text}")

    async def get_match_related_data(self, match_endpoint: str) -> GameDTO | ReducedGameDTO:
        """Get game related data for a given game. THings like attendance, home team, away team etc.

        Args:
            match_endpoint (str): Endpoint url for a specific afl match

        Returns:
            GameDTO | ReducedGameDTO: Either return a full GameDTO which is then added to the set, or a ReducedDTO
            which is used to query player stats.
        """

        logger.info("Getting game related data")
        response = await self.client.get(f"{self.base_url}{match_endpoint}")

        if response.status_code == httpx.codes.OK:

            soup = BeautifulSoup(response.text, "html.parser")

            full_table = soup.find("table")
            all_rows = full_table.find_all("tr")

            match_scores_dto = self._get_match_score_data(all_rows)
            metadata_dto = await self._get_match_metadata(all_rows, match_scores_dto.home_team, match_scores_dto.away_team)

            if isinstance(metadata_dto, ReducedGameDTO):
                return metadata_dto
            
            if metadata_dto is not None:
                logger.info("Adding game to DTO")
                game_dto = GameDTO(**metadata_dto.model_dump(), **match_scores_dto.model_dump())
                logger.info(f"game dto: {game_dto}")
                self.scraped_games.add(game_dto)
        else:
            logger.error(f"❌ Failed to fetch match metadata and score data. Status: {response.status_code}")
            logger.info(f"Response content: {response.content}")

    async def get_player_stats_for_match(self,
        match_endpoint: str,
        game_id: str,
        home_team: str,
        away_team: str,
        round_id: str,
        year: int
    ) -> None:
        
        """Get the individual player stats (Kicks, Disposals etc.) for a given match

        Args:
            match_endpoint (str): The url which contains stats for the given match
            game_id (str): GameId referring the given match
            home_team (str): Name of the home team
            away_team (str): Name of the away team
            round_id (str): RoundId for the given match
            year (int): Year of the match

        Returns:
            Tuple[List[PlayerMatchStatsDTO], List[PlayerProfileDTO]]: Tuple containing a list 
            of the PlayerMatchStatsDTO and a list of PlayerProfileDTO
        """
        logger.info(f"Getting player stats for game: {game_id}")
        match_stats_tables = await self._get_table_element_from_page(match_endpoint)     

        if not match_stats_tables:
            # if the stats don't exist return a tuple of empty sets
            return None
        
        for index, table in enumerate(match_stats_tables):
            rows = table.find_all("tr")[2:]  # skip header rows
            for row in rows:
                cells = row.find_all("td") # get all the cells
                if len(cells) < 25:
                    continue  # skip malformed or empty rows
                
                # Get the players name
                player_link = cells[1].find("a")["href"] # url for player profile
                display_name = cells[1].get_text(strip=True)

                # get the D.O.B from the player profile
                dob = await self._get_player_dob(player_link, year)
                if not dob:
                    continue

                key = (display_name, dob)

                async with self._player_lock:
                    if key in self.player_tracker:
                        logger.info(f"{display_name} already scraped")
                        continue
                    self.player_tracker.add(key)

                # check if the player exists by querying display_name and dob
                player_exists = await self.player_service.check_if_player_in_db(display_name, dob)

                if player_exists:
                    player_id = await self.player_service.get_player_id(display_name, dob)
                else:
                    # create a player profile dto which will then be inserted into the db
                    logger.info(f"Scraping profile data for {display_name}")
                    player_profile = await self.footy_wire_scraper.get_player_profile_stats(
                        team_name=home_team if index == 0 else away_team,
                        display_name=display_name,
                        dob=dob
                    )

                    if player_profile:
                        self.scraped_players.add(player_profile)
                        player_id = player_profile.player_id # need to set the player_id value for the next dto
                
                if not player_id:
                    continue # skip stats if no player ID

                # Map field names to their corresponding int values from cells[2:25]
                # Unpack dictionary to form DTO
                stat_exists = await self.stat_service.check_if_stat_exists(game_id, player_id)
                if not stat_exists:
                    stat_values = {
                        field: int(cells[i + 2].get_text(strip=True) or 0) 
                        for i, field in enumerate(field_names)
                    }

                    player_stats_dto = PlayerMatchStatsDTO(
                        player_name=display_name,
                        player_id=player_id,
                        game_id=game_id,
                        team=home_team if index == 0 else away_team,
                        year=year,
                        round=round_id,
                        **stat_values
                    )
                    
                    self.scraped_stats.add(player_stats_dto)
            
    async def _get_match_metadata(
            self,
            all_rows: ResultSet,
            home_team: str,
            away_team: str
    ) -> MatchMetadataDTO | ReducedGameDTO | None:
        """Scrape metadata of a specific match from afl tables website

        Args:
            all_rows (ResultSet): A collection of all of the rows from the HTML table containing the metadata

        Returns:
            MatchMetadataDTO: DTO which holds the relevant match related data
        """

        logger.info("Getting match metadata (i.e. Attendance, Venue, etc.)")
        metadata_string = all_rows[0].find("td", attrs={"align": "center"}).get_text(strip=True)

        # string returned is not in a useful format. Use a regex expression to extract the required data
        pattern = r"Round:([\w\s]+?)Venue:(.*?)Date:.*?(\d{1,2}-\w{3}-\d{4}) (\d{1,2}:\d{2} [AP]M).*?Attendance:(\d+)"
        match = re.search(pattern, metadata_string)
        
        logger.info("Checking input against regex pattern")
        if match:
            round_label = match.group(1).strip() # get the round from the string
            round_code = FINALS_ROUND_MAP.get(round_label, round_label)

            year = match.group(3).split("-")[2] # get the year from the string
            date = convert_date_format(match.group(3))
            # increment the game index counter
            self.game_index_counter[round_code] += 1
            game_index = self.game_index_counter[round_code]

            # Build the game id string
            if round_code not in FINALS_ROUND_MAP.values():
                game_id = f"{year}R{int(match.group(1)):02d}{game_index:02d}"
            else:
                logger.info(f"Building game id for a finals match: {metadata_string}")
                game_id = f"{year}{round_code}{game_index:02d}"

            game_exists = await self.game_service.check_if_game_exists(date, home_team, away_team)

            if not game_exists:
                # only want to add the dto if it doesn't already exist in the db
                logger.info("Game does not exist in db, extracting data into DTO")
                metadata_dto = MatchMetadataDTO(
                    game_id = game_id,
                    year=year,
                    round_id = round_code,
                    venue = match.group(2).strip(),
                    date = match.group(3),
                    start_time = match.group(4),
                    attendance = int(match.group(5))
                )
            else:
                logger.info("Game exists in db")
                # return a reduced DTO with enough data to search for player stats
                return ReducedGameDTO(
                    game_id=game_id,
                    home_team=home_team,
                    away_team=away_team,
                    round_id=round_code
                )
        else:
            logger.warning("No regex match found")
            return None

        return metadata_dto
    
    def _get_match_score_data(self, all_rows: ResultSet) -> MatchScoreDTO:
        """Get the data related to the match score from the afl tables website

        Args:
            all_rows (ResultSet): A collection of all of the rows from the HTML table containing the metadata

        Returns:
            MatchScoreDTO: DTO which holds the relevant match score related data
        """
        remaining_rows = all_rows[1:3] # skip the header row

        teams = []
        scores_list = []

        # loop through rows and get the game score data and store it in the respective list
        for row in remaining_rows:
            cells = row.find_all("td")
            team_name = cells[0].get_text(strip=True)
            logger.info(f"Getting score data for {team_name}")

            # afl scores follow and Goal.Behind.Total format. We just want the first 2
            score_data = [before_second_dot(cells[i].get_text(strip=True)) for i in range(1, 5)]
            final_score = cells[4].get_text(strip=True).split(".")[2] # Get the final score of the game

            teams.append(team_name)
            scores_list.append({
                "qt": score_data[0],
                "ht": score_data[1],
                "3qt": score_data[2],
                "ft": score_data[3],
                "final_score": final_score
            })

        return MatchScoreDTO(
            home_team=teams[0],
            home_team_score_qt=scores_list[0].get("qt"),
            home_team_score_ht=scores_list[0].get("ht"),
            home_team_score_3qt=scores_list[0].get("3qt"),
            home_team_score_ft=scores_list[0].get("ft"),
            home_team_score=scores_list[0].get("final_score"),
            away_team=teams[1],
            away_team_score_qt=scores_list[1].get("qt"),
            away_team_score_ht=scores_list[1].get("ht"),
            away_team_score_3qt=scores_list[1].get("3qt"),
            away_team_score_ft=scores_list[1].get("ft"),
            away_team_score=scores_list[1].get("final_score")
        )

    async def _get_table_element_from_page(self, match_endpoint) -> List | bool:
        response = await self.client.get(f"{self.base_url}{match_endpoint}")
        if response.status_code == httpx.codes.OK:
            soup = BeautifulSoup(response.text, "html.parser")
    
            # Get all tables with class 'sortable' and Match Statistics in the header
            logger.info("Getting match stats table")
            sortable_tables = soup.find_all("table", class_="sortable")
            match_stats_tables = [table for table in sortable_tables if "Match Statistics" in table.find("th").get_text(strip=True)]
            return match_stats_tables
        else:
            logger.warning("Match stats table not found")
            return False
    
    async def _get_player_dob(self, player_link: str, year: int) -> str | bool:
        """Scrape the date of birth from the html

        Args:
            player_link (str): Endpoint url for given player's profile

        Returns:
            str: Dob as a string
        """
        try:
            if player_link in self.dob_cache:
                return self.dob_cache[player_link]

            response = await self.client.get(urljoin(f"{self.base_url}games/{year}/", player_link)) #FIXME: fudged url to work with player_link value
            if response.status_code == httpx.codes.OK:
                soup = BeautifulSoup(response.text, "html.parser")
                born_b_tag = soup.find("b", string=re.compile(r"Born:"))
                # Extract the text that comes after "Born:" and format it
                if born_b_tag:
                    # Use regex to extract the date portion
                    dob = born_b_tag.next_sibling.replace("(", "").strip()
                else:
                    print("DOB not found")
                
                self.dob_cache[player_link] = dob
                return dob
            else:
                logger.warning("Get request failed so dob not scraped")
                logger.info("Returning False")
                return False
        except httpx.ReadTimeout:
            logger.warning(f"Failed to get DOB for {player_link}")
            return False
        
