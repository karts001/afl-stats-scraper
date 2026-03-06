from typing import List
from dtos.games_dto import GameDTO
from repositories.game_repository import GameRepository


class GameService():
    def __init__(self, repo: GameRepository):
        self.repo = repo

    async def check_if_game_exists(self, date: str, home_team: str, away_team: str) -> bool:
        return await self.repo.check_game_exists(date, home_team, away_team)

    async def insert_games(self, game_dtos: List[GameDTO]) -> None:
        await self.repo.insert_games(game_dtos)

    async def get_game_id(self, date: str, home_team: str, away_team: str) -> str:
        return await self.repo.get_game_id(date, home_team, away_team)
