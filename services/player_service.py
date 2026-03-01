from typing import List
from dtos.player_profile_dto import PlayerProfileDTO
from repositories.player_repository import PlayerRepository


class PlayerService():
    def __init__(self, repo: PlayerRepository):
        self.repo = repo

    async def check_if_player_in_db(self, display_name: str, dob: str) -> bool:
        return await self.repo.check_player_exists(display_name, dob)

    async def insert_players(self, player_dtos: List[PlayerProfileDTO]) -> None:
        await self.repo.insert_players(player_dtos)

    async def get_player_id(self, display_name: str, dob: str) -> str | None:
        await self.repo.get_player_id(display_name, dob)

    def check_if_player_in_dto_set(self, display_name, dob, dtos: List[PlayerProfileDTO]) -> str | None:
        for dto in dtos:
            if dto.display_name == display_name and dto.dob == dob:
                return dto.player_id
        
        return None
