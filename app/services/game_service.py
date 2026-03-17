from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.models import DailyWord, Game, Guess, Player, ShareLink
from app.services.game_logic import encode_result_mask, evaluate_guess, is_win_mask
from app.services.time_service import day_key, day_start_utc, day_index, local_today, utc_now
from app.services.word_data import task_for_day, task_for_day_index, load_dictionary

MAX_ATTEMPTS = 6
WORD_LENGTH = 5


class GameError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DayUnavailableError(GameError):
    def __init__(self) -> None:
        super().__init__("Задания закончились, сегодня слово недоступно.", 409)


class InvalidWordError(GameError):
    def __init__(self) -> None:
        super().__init__("Һүҙлектә юҡ!", 400)


class GuessLengthError(GameError):
    def __init__(self) -> None:
        super().__init__("5 хәреф яҙығыҙ!", 400)


class GameAlreadyFinishedError(GameError):
    def __init__(self) -> None:
        super().__init__("Игра на сегодня уже завершена.", 409)


@dataclass
class GuessResult:
    guess: Guess
    game: Game
    daily_word: DailyWord
    place: int | None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_or_create_player(db: Session, cookie_sid: str | None) -> tuple[Player, str | None]:
    now = utc_now()
    if cookie_sid:
        player = db.scalar(select(Player).where(Player.cookie_id == cookie_sid))
        if player:
            player.last_seen_at = now
            db.commit()
            return player, None

    sid = uuid.uuid4().hex
    player = Player(cookie_id=sid, created_at=now, last_seen_at=now)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player, sid


def _daily_word_query_for_day(day: str) -> Select[tuple[DailyWord]]:
    return select(DailyWord).where(DailyWord.day_key == day)


def ensure_daily_word(db: Session, settings: Settings, today) -> DailyWord | None:
    today_key = day_key(today)
    existing = db.scalar(_daily_word_query_for_day(today_key))
    if existing:
        return existing

    task_info = task_for_day(settings, today)
    if task_info is None:
        return None
    task_idx, task = task_info

    daily = DailyWord(
        day_key=today_key,
        task_index=task_idx,
        word=task.word,
        description=task.description,
        opened_at_utc=day_start_utc(settings, today),
    )
    db.add(daily)
    db.commit()
    db.refresh(daily)
    return daily


def get_game_for_player_and_day(db: Session, player_id: int, daily_word_id: int) -> Game | None:
    stmt = (
        select(Game)
        .options(joinedload(Game.guesses))
        .where(Game.player_id == player_id, Game.daily_word_id == daily_word_id)
    )
    return db.scalar(stmt)


def get_or_create_game(db: Session, player: Player, daily_word: DailyWord) -> Game:
    game = get_game_for_player_and_day(db, player.id, daily_word.id)
    if game:
        return game

    now = utc_now()
    game = Game(
        player_id=player.id,
        daily_word_id=daily_word.id,
        status="in_progress",
        started_at=now,
        finished_at=None,
        attempts_used=None,
        win_elapsed_seconds=None,
        win_attempt_no=None,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def _leaderboard_games(db: Session, daily_word_id: int, limit: int | None = None) -> list[tuple[Game, Player]]:
    stmt = (
        select(Game, Player)
        .join(Player, Player.id == Game.player_id)
        .where(Game.daily_word_id == daily_word_id, Game.status == "won")
        .order_by(Game.win_elapsed_seconds.asc(), Game.finished_at.asc(), Game.id.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = db.execute(stmt).all()
    return rows


def leaderboard_for_day(db: Session, daily_word_id: int, limit: int = 10) -> list[dict]:
    rows = _leaderboard_games(db, daily_word_id, limit)
    leaderboard = []
    for idx, (game, player) in enumerate(rows, start=1):
        leaderboard.append(
            {
                "place": idx,
                "player_label": f"Игрок #{player.id}",
                "attempts_used": game.attempts_used or 0,
                "win_elapsed_seconds": game.win_elapsed_seconds or 0,
            }
        )
    return leaderboard


def place_for_game(db: Session, game: Game) -> int | None:
    if game.status != "won":
        return None
    rows = _leaderboard_games(db, game.daily_word_id, None)
    for idx, (row_game, _row_player) in enumerate(rows, start=1):
        if row_game.id == game.id:
            return idx
    return None


def submit_guess(db: Session, settings: Settings, player: Player, guess_raw: str) -> GuessResult:
    guess_word = guess_raw.strip().lower()
    if len(guess_word) != WORD_LENGTH:
        raise GuessLengthError()

    today = local_today(settings)
    daily_word = ensure_daily_word(db, settings, today)
    if daily_word is None:
        raise DayUnavailableError()

    dictionary = load_dictionary(settings)
    if guess_word not in dictionary:
        raise InvalidWordError()

    game = get_or_create_game(db, player, daily_word)
    if game.status != "in_progress":
        raise GameAlreadyFinishedError()

    attempt_no = len(game.guesses) + 1
    if attempt_no > MAX_ATTEMPTS:
        raise GameAlreadyFinishedError()

    result_states = evaluate_guess(guess_word, daily_word.word)
    result_mask = encode_result_mask(result_states)
    now = utc_now()

    guess = Guess(
        game_id=game.id,
        attempt_no=attempt_no,
        guess_word=guess_word,
        result_mask=result_mask,
        submitted_at=now,
    )
    db.add(guess)

    if is_win_mask(result_mask):
        game.status = "won"
        game.finished_at = now
        game.attempts_used = attempt_no
        game.win_attempt_no = attempt_no
        elapsed = now - _as_utc(daily_word.opened_at_utc)
        game.win_elapsed_seconds = max(0, int(elapsed.total_seconds()))
    elif attempt_no >= MAX_ATTEMPTS:
        game.status = "lost"
        game.finished_at = now
        game.attempts_used = attempt_no

    db.commit()
    db.refresh(guess)

    game = get_game_for_player_and_day(db, player.id, daily_word.id)
    assert game is not None
    place = place_for_game(db, game)
    return GuessResult(guess=guess, game=game, daily_word=daily_word, place=place)


def serialize_guess(guess: Guess) -> dict:
    return {
        "attempt_no": guess.attempt_no,
        "guess_word": guess.guess_word,
        "result_mask": guess.result_mask,
        "submitted_at": guess.submitted_at,
    }


def build_game_state(db: Session, game: Game | None, daily_word: DailyWord | None) -> dict:
    if game is None or daily_word is None:
        return {
            "status": "unavailable",
            "max_attempts": MAX_ATTEMPTS,
            "word_length": WORD_LENGTH,
            "current_row": 0,
            "guesses": [],
            "answer": None,
            "description": None,
            "place": None,
            "win_elapsed_seconds": None,
        }

    include_answer = game.status == "won"
    return {
        "status": game.status,
        "max_attempts": MAX_ATTEMPTS,
        "word_length": WORD_LENGTH,
        "current_row": len(game.guesses),
        "guesses": [serialize_guess(g) for g in sorted(game.guesses, key=lambda x: x.attempt_no)],
        "answer": daily_word.word if include_answer else None,
        "description": daily_word.description if include_answer else None,
        "place": place_for_game(db, game) if game.status == "won" else None,
        "win_elapsed_seconds": game.win_elapsed_seconds,
    }


def build_history_last_10_days(db: Session, settings: Settings, player: Player, today) -> list[dict]:
    days = [today - timedelta(days=i) for i in range(1, 11)]
    day_keys = [day_key(day) for day in days]

    stmt = (
        select(Game, DailyWord)
        .join(DailyWord, DailyWord.id == Game.daily_word_id)
        .options(joinedload(Game.guesses))
        .where(Game.player_id == player.id, DailyWord.day_key.in_(day_keys))
    )
    played_by_day: dict[str, tuple[Game, DailyWord]] = {}
    for game, daily in db.execute(stmt).unique().all():
        played_by_day[daily.day_key] = (game, daily)

    history: list[dict] = []
    for day in days:
        key = day_key(day)
        existing = played_by_day.get(key)
        if existing:
            game, daily = existing
            place = place_for_game(db, game) if game.status == "won" else None
            history.append(
                {
                    "day": key,
                    "word": daily.word,
                    "description": daily.description,
                    "user_status": game.status,
                    "attempts_used": game.attempts_used,
                    "game_id": game.id,
                    "guesses": [serialize_guess(g) for g in sorted(game.guesses, key=lambda x: x.attempt_no)],
                    "place": place,
                    "win_elapsed_seconds": game.win_elapsed_seconds,
                }
            )
            continue

        idx = day_index(settings, day)
        task = task_for_day_index(settings, idx)
        if task is None:
            continue
        history.append(
            {
                "day": key,
                "word": task.word,
                "description": task.description,
                "user_status": "not_played",
                "attempts_used": None,
                "game_id": None,
                "guesses": [],
                "place": None,
                "win_elapsed_seconds": None,
            }
        )

    return history


def build_achievements(db: Session, settings: Settings, player: Player) -> dict:
    today = local_today(settings)

    # Get all days this player won, ordered desc
    stmt = (
        select(DailyWord.day_key)
        .join(Game, Game.daily_word_id == DailyWord.id)
        .where(Game.player_id == player.id, Game.status == "won")
        .order_by(DailyWord.day_key.desc())
    )
    won_days_set = {row[0] for row in db.execute(stmt).all()}

    # Count current win streak backwards from today (or yesterday if today not won yet)
    streak = 0
    check_day = today
    if day_key(today) not in won_days_set:
        check_day = today - timedelta(days=1)
    while day_key(check_day) in won_days_set:
        streak += 1
        check_day = check_day - timedelta(days=1)

    # Check if player was first to answer today
    first_today = False
    daily_word = ensure_daily_word(db, settings, today)
    if daily_word is not None:
        game = get_game_for_player_and_day(db, player.id, daily_word.id)
        if game is not None and game.status == "won":
            place = place_for_game(db, game)
            first_today = place == 1

    # Total games played by this player
    total_played = db.scalar(
        select(func.count(Game.id))
        .where(Game.player_id == player.id)
    ) or 0

    return {
        "streak_3": streak >= 3,
        "streak_5": streak >= 5,
        "streak_10": streak >= 10,
        "streak_25": streak >= 25,
        "streak_50": streak >= 50,
        "first_today": first_today,
        "tried_30": int(total_played) >= 30,
        "win_streak": streak,
        "total_played": int(total_played),
    }


def build_totals(db: Session, player: Player) -> dict:
    guesses_total = db.scalar(select(func.count(Guess.id))) or 0
    wins_total = db.scalar(select(func.count(Game.id)).where(Game.status == "won")) or 0
    played_total = db.scalar(select(func.count(Game.id))) or 0

    your_played = db.scalar(select(func.count(Game.id)).where(Game.player_id == player.id)) or 0
    your_wins = (
        db.scalar(select(func.count(Game.id)).where(Game.player_id == player.id, Game.status == "won")) or 0
    )

    return {
        "guesses_total": int(guesses_total),
        "wins_total": int(wins_total),
        "played_total": int(played_total),
        "your_played": int(your_played),
        "your_wins": int(your_wins),
    }


def get_today_context(db: Session, settings: Settings, player: Player) -> tuple[bool, DailyWord | None, Game | None, str]:
    today = local_today(settings)
    today_key = day_key(today)
    daily_word = ensure_daily_word(db, settings, today)
    if daily_word is None:
        return False, None, None, today_key

    game = get_or_create_game(db, player, daily_word)
    return True, daily_word, game, today_key


def get_finished_game_for_player(db: Session, player_id: int, game_id: int) -> Game | None:
    stmt = (
        select(Game)
        .options(joinedload(Game.guesses), joinedload(Game.daily_word))
        .where(Game.id == game_id, Game.player_id == player_id)
    )
    return db.scalar(stmt)


def get_or_create_share_link(db: Session, settings: Settings, game: Game) -> ShareLink:
    existing = db.scalar(select(ShareLink).where(ShareLink.game_id == game.id))
    if existing:
        return existing

    while True:
        token = secrets.token_urlsafe(settings.share_token_bytes)
        collision = db.scalar(select(ShareLink).where(ShareLink.token == token))
        if not collision:
            break

    share = ShareLink(game_id=game.id, token=token, created_at=utc_now())
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def get_share_payload(db: Session, token: str) -> dict | None:
    stmt = (
        select(ShareLink)
        .options(joinedload(ShareLink.game).joinedload(Game.guesses), joinedload(ShareLink.game).joinedload(Game.daily_word))
        .where(ShareLink.token == token)
    )
    share = db.scalar(stmt)
    if not share:
        return None

    game = share.game
    daily = game.daily_word
    place = place_for_game(db, game)

    return {
        "day": daily.day_key,
        "word": daily.word,
        "description": daily.description,
        "status": game.status,
        "attempts_used": game.attempts_used,
        "win_elapsed_seconds": game.win_elapsed_seconds,
        "place": place,
        "guesses": [serialize_guess(g) for g in sorted(game.guesses, key=lambda x: x.attempt_no)],
    }


def share_answer_visible(settings: Settings, day_key_value: str) -> bool:
    # Reveal answer only after next day has started in UTC+5.
    day = date.fromisoformat(day_key_value)
    return local_today(settings) > day


def apply_share_visibility(settings: Settings, payload: dict) -> dict:
    if share_answer_visible(settings, payload["day"]):
        return payload

    updated = dict(payload)
    updated["word"] = "иртәгә әйтәм"
    updated["description"] = "иртәгә әйтәм"
    return updated
