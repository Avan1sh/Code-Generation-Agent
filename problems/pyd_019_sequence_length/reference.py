from pydantic import BaseModel, Field


class Playlist(BaseModel):
    name: str
    tracks: list[str] = Field(min_length=1, max_length=3)
