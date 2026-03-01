from typing import Optional
from pydantic import BaseModel, Field

class MatchMetadataDTO(BaseModel):
    game_id: str
    year: int
    round_id: str
    venue: str
    attendance: int # convert to int before inserting into db?
    date: str
    start_time: str

class MatchScoreDTO(BaseModel):
    home_team: str
    home_team_score_qt: str
    home_team_score_ht: str
    home_team_score_3qt: str
    home_team_score_ft: str
    home_team_score: int
    away_team: str
    away_team_score_qt: str
    away_team_score_ht: str
    away_team_score_3qt: str
    away_team_score_ft: str
    away_team_score: int

class ReducedGameDTO(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    round_id: str
    
class GameDTO(BaseModel):
    game_id: str = Field(alias="GameId")
    year: int = Field(alias="Year")
    round_id: str = Field(alias="Round")
    venue: str = Field(alias="Venue")
    attendance: int = Field(alias="Attendance")
    date: str = Field(alias="Date")
    start_time: str = Field(alias="StartTime")
    home_team: str = Field(alias="HomeTeam")
    home_team_score_qt: str = Field(alias="HomeTeamScoreQt")
    home_team_score_ht: str = Field(alias="HomeTeamScoreHT")
    home_team_score_3qt: str = Field(alias="HomeTeamScore3QT")
    home_team_score_ft: str = Field(alias="HomeTeamScoreFT")
    home_team_score: int = Field(alias="HomeTeamScore")
    away_team: str = Field(alias="AwayTeam")
    away_team_score_qt: str = Field(alias="AwayTeamScoreQT")
    away_team_score_ht: str = Field(alias="AwayTeamScoreHT")
    away_team_score_3qt: str = Field(alias="AwayTeamScore3QT")
    away_team_score_ft: str = Field(alias="AwayTeamScoreFT")
    away_team_score: int = Field(alias="AwayTeamScore")
    max_temp: Optional[float] = Field(alias="MaxTemp", default=None)
    min_temp: Optional[float] = Field(alias="MinTemp", default=None)
    rainfall: Optional[float] = Field(alias="Rainfall", default=None)
    
    class Config:
        validate_by_name = True
        frozen=True
