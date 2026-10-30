from pydantic import BaseModel, Field


class CardRuling(BaseModel):
    source: str
    published_at: str
    comment: str


class MTGCard(BaseModel):
    id: str
    name: str
    mana_cost: str
    type_line: str
    oracle_text: str
    image_uri: str | None = None
    rulings: list[CardRuling] = Field(default_factory=list)

    @classmethod
    def from_scryfall_json(cls, data: dict, rulings: list[CardRuling] | None = None) -> "MTGCard":
        """
        Parses json data from scryfall api and converts it to MTGCard object.

        Args:
            data: JSON data from scryfall api.
            rulings: list[CardRuling] rules list from scryfall api.

        Returns:
            card: MTGCard object containing card details and rulings.
        """
        # ----- Resolve mana cost, this can be a combination of 0-9 and/or (W)hite, bl(U)e, (B)lack, (R)ed, (G)reen. -----
        # ----- A card can have dual faces - called MDFC, so we need to handle the mana cost of those too.

        oracle_text = data.get("oracle_text")
        mana_cost = data.get("mana_cost", "0")

        if oracle_text is None and "card_faces" in data:
            oracle_text = "\n//\n".join(
                face.get("oracle_text", "") for face in data["card_faces"]
            )
            mana_cost = " // ".join(
                face.get("mana_cost", "") for face in data["card_faces"] if face.get("mana_cost")
            )

        image_uri = None
        if "image_uris" in data:
            image_uri = data["image_uris"].get("normal")
        elif "card_faces" in data:
            image_uri = data["card_faces"][0].get("image_uris", {}).get("normal")


        return cls(
            id=data.get("id"),
            name=data.get("name"),
            mana_cost=mana_cost or "0",
            type_line=data.get("type_line"),
            oracle_text=oracle_text or "",
            image_uri=image_uri,
            rulings=rulings or [],

        )

