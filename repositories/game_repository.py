from typing import Set

from repositories.base_repository import BaseRepository
from dtos.games_dto import GameDTO

from logger import logger

class GameRepository(BaseRepository): 
    async def check_game_exists(self, date: str, home_team: str, away_team: str) -> bool:
        query = """
            SELECT 1
            FROM games
            WHERE Date = $1 AND HomeTeam = $2 AND AwayTeam = $3
            LIMIT 1
        """
        logger.info(f"date: {date}, home_team: {home_team}, away_team: {away_team}")
        result = await self.fetch_one(query, (date, home_team, away_team))

        return result is not None

    async def insert_games(self, game_dtos: Set[GameDTO]) -> None:
        if not game_dtos:
            return
        
        columns, placeholders, values = self.get_columns_placeholders_and_values(game_dtos)

        query = f"""
            INSERT INTO games
            ({columns}) VALUES ({placeholders})
            ON CONFLICT (GameId) DO NOTHING
        """
        await self.execute_batch(query, values)

    async def get_game_id(self, date:str, home_team: str, away_team: str) -> str:
        query = """
            SELECT gameid FROM games
            WHERE Date = $1 AND hometeam =$2 AND awayteam = $3
            LIMIT 1
        """

        result = await self.fetch_one(query, (date, home_team, away_team))
        
        return result['gameid']

        