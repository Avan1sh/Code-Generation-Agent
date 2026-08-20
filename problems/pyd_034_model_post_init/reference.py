from typing import Any

from pydantic import BaseModel, PrivateAttr


class Document(BaseModel):
    text: str

    _word_count: int = PrivateAttr(default=0)

    def model_post_init(self, __context: Any) -> None:
        self._word_count = len(self.text.split())

    @property
    def word_count(self) -> int:
        return self._word_count
