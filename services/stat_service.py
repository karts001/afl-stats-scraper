from typing import List
from dtos.stats_dto import PlayerMatchStatsDTO
from repositories.stats_repository import StatRepository


class StatService():
    def __init__(self, repo: StatRepository):
        self.repo = repo

    async def check_if_stat_exists(self, game_id: str, player_id: str) -> bool:
        await self.repo.check_stat_exists(game_id, player_id)

    async def insert_stats(self, player_dtos: set[PlayerMatchStatsDTO]) -> None:
        await self.repo.insert_stats(player_dtos)
