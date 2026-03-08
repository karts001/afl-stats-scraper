from pydantic import BaseModel, ConfigDict, Field

class PlayerMatchStatsDTO(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        frozen=True,
        populate_by_name=True
    )
    game_id: str = Field(alias="GameId")
    team: str = Field(alias="Team")
    year: int = Field(alias="Year")
    round: str = Field(alias="Round")
    player_id: str = Field(alias="PlayerId")
    player_name: str = Field(alias="DisplayName")
    kicks: int = Field(alias="Kicks")
    marks: int = Field(alias="Marks")
    handballs: int = Field(alias="Handballs")
    disposals: int = Field(alias="Disposals")
    goals: int = Field(alias="Goals")
    behinds: int = Field(alias="Behinds")
    tackles: int = Field(alias="Tackles")
    hitouts: int = Field(alias="Hitouts")
    clearances: int = Field(alias="Clearances")
    clangers: int = Field(alias="Clangers")
    free_kicks_for: int = Field(alias="Frees")
    free_kicks_against: int = Field(alias="FreesAgainst")
    rebound50s: int = Field(alias="Rebounds")
    inside50s: int = Field(alias="Inside50s")
    brownlow_votes: int = Field(alias="BrownlowVotes")
    contested_possessions: int = Field(alias="ContestedPossessions")
    uncontested_possessions: int = Field(alias="UncontestedPossessions")
    contested_marks: int = Field(alias="ContestedMarks")
    marks_inside: int = Field(alias="MarksInside50")
    one_percenters: int = Field(alias="OnePercenters")
    bounces: int = Field(alias="Bounces")
    goal_assist: int = Field(alias="GoalAssists")
    percent_played: int = Field(alias="PercentPlayed")
