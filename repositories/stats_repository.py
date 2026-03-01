from typing import List
from dtos.stats_dto import PlayerMatchStatsDTO
from repositories.base_repository import BaseRepository


class StatRepository(BaseRepository):
    async def check_stat_exists(self, game_id: str, player_id: str) -> bool:
        query = """
            SELECT 1
            FROM stats
            WHERE GameId ILIKE $1 and PlayerId ILIKE $2
            LIMIT 1
        """
        result = await self.fetch_one(query, (game_id, player_id))

        return result is not None
    
    async def insert_stats(self, stat_dtos: List[PlayerMatchStatsDTO]) -> None:
        if not stat_dtos:
            return
        
        columns, placeholders, values = self.get_columns_placeholders_and_values(stat_dtos)
        
        query = f"""
            INSERT INTO stats
            ({columns}) VALUES ({placeholders})
            ON CONFLICT (GameId, PlayerId) DO NOTHING
        """
        await self.execute_batch(query, values)