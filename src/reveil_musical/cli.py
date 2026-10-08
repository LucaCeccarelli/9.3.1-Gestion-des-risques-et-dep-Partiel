"""Point d'entrée : `reveil-musical <user_id> <jour> <météo>` (l'ordonnancement est externe)."""

import argparse
import logging

from reveil_musical.container import Container
from reveil_musical.domain import Day, Weather


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Déclenche le réveil musical d'un utilisateur.")
    parser.add_argument("user_id")
    parser.add_argument("day", type=Day, choices=list(Day))
    parser.add_argument("weather", type=Weather, choices=list(Weather))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    Container().wake_up_service().wake_up(args.user_id, args.day, args.weather)
