"""Point d'entrée HTTP : POST /wake-up, appelé par l'ordonnanceur (externe) à l'heure du réveil."""

import logging

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from reveil_musical.container import Container
from reveil_musical.domain import Channel, Day, Weather
from reveil_musical.users import UnknownUser
from reveil_musical.wake_up import WakeUpService


class WakeUpRequest(BaseModel):
    user_id: str
    day: Day
    weather: Weather


class WakeUpResponse(BaseModel):
    user_id: str
    channel: Channel
    day: Day
    weather: Weather
    track_title: str
    track_artist: str
    text: str


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container()
    app = FastAPI(title="Réveil musical", version="0.1.0")

    def get_service() -> WakeUpService:
        return container.wake_up_service()

    @app.post("/wake-up", response_model=WakeUpResponse)
    def wake_up(
        request: WakeUpRequest, service: WakeUpService = Depends(get_service)
    ) -> WakeUpResponse:
        try:
            msg = service.wake_up(request.user_id, request.day, request.weather)
        except UnknownUser:
            raise HTTPException(404, f"utilisateur inconnu : {request.user_id}") from None
        return WakeUpResponse(
            user_id=msg.user_id,
            channel=msg.channel,
            day=msg.day,
            weather=msg.weather,
            track_title=msg.track.title,
            track_artist=msg.track.artist,
            text=msg.text,
        )

    return app


def run() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    uvicorn.run("reveil_musical.api:create_app", factory=True, host="127.0.0.1", port=8000)
