from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GuessRequest(BaseModel):
    guess: str = Field(..., min_length=5, max_length=5)


class GuessItemOut(BaseModel):
    attempt_no: int
    guess_word: str
    result_mask: str
    submitted_at: datetime


class LeaderboardItemOut(BaseModel):
    place: int
    player_label: str
    attempts_used: int
    win_elapsed_seconds: int


class HistoryItemOut(BaseModel):
    day: str
    word: str
    description: str
    user_status: str
    attempts_used: int | None = None
    game_id: int | None = None
    guesses: list[GuessItemOut] = []
    place: int | None = None
    win_elapsed_seconds: int | None = None


class TotalsOut(BaseModel):
    guesses_total: int
    wins_total: int
    played_total: int
    your_played: int
    your_wins: int


class AchievementsOut(BaseModel):
    streak_3: bool = False
    streak_5: bool = False
    streak_10: bool = False
    streak_25: bool = False
    streak_50: bool = False
    first_today: bool = False
    tried_30: bool = False
    win_streak: int = 0
    total_played: int = 0


class GameStateOut(BaseModel):
    status: str
    max_attempts: int
    word_length: int
    current_row: int
    guesses: list[GuessItemOut]
    answer: str | None = None
    description: str | None = None
    place: int | None = None
    win_elapsed_seconds: int | None = None


class StateOut(BaseModel):
    today: str
    day_available: bool
    game_state: GameStateOut
    leaderboard_top: list[LeaderboardItemOut]
    history_last_10_days: list[HistoryItemOut]
    totals: TotalsOut
    achievements: AchievementsOut


class GuessResponseOut(BaseModel):
    guess: GuessItemOut
    game_state: GameStateOut
    leaderboard_top: list[LeaderboardItemOut]
    totals: TotalsOut
    achievements: AchievementsOut


class ShareCreateResponse(BaseModel):
    url: str


class ShareDataOut(BaseModel):
    day: str
    word: str
    description: str
    status: str
    attempts_used: int | None
    win_elapsed_seconds: int | None
    place: int | None
    guesses: list[GuessItemOut]
