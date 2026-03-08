from typing import Set
from dtos.player_profile_dto import PlayerProfileDTO
from repositories.base_repository import BaseRepository


class PlayerRepository(BaseRepository):
    async def check_player_exists(self, display_name: str, dob: str) -> bool:
        query = """
            SELECT *
            FROM players
            WHERE DisplayName ILIKE $1 AND Dob = $2
            LIMIT 1
        """
        result = await self.fetch_one(query, (display_name, dob))

        return result is not None
    
    async def insert_players(self, player_dtos: Set[PlayerProfileDTO]):
        if not player_dtos:
            return
        
        columns, placeholders, values = self.get_columns_placeholders_and_values(player_dtos)

        query = f"""
            INSERT INTO players
            ({columns}) VALUES ({placeholders})
            ON CONFLICT (PlayerId) DO NOTHING
        """

        await self.execute_batch(query, values)

    async def get_player_id(self, display_name: str, dob: str) -> str | None:
        query = """
            SELECT playerId
            FROM players
            WHERE DisplayName ILIKE $1 AND Dob = $2
            LIMIT 1
        """
        result = await self.fetch_one(query, (display_name, dob))

        if result:
            return result['playerid']
        
        return None
