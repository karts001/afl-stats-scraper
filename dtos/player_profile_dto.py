from typing import Optional
from pydantic import BaseModel, Field

class PlayerProfileDTO(BaseModel):
    player_id: str = Field(alias="PlayerId")
    display_name: str = Field(alias="DisplayName")
    height: Optional[int] = Field(alias="Height", default=None)
    weight: Optional[int] = Field(alias="Weight", default=None)
    dob: str = Field(alias="Dob")
    position: str = Field(alias="Position")
    origin: str = Field(alias="Origin")

    class Config:
        validate_by_name = True
        frozen=True
    
