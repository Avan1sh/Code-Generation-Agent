from pydantic import RootModel


class Tags(RootModel[list[str]]):
    pass


def parse_tags(raw: str) -> Tags:
    return Tags.model_validate_json(raw)
