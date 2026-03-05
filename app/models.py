from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cookie_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    games: Mapped[list[Game]] = relationship("Game", back_populates="player")


class DailyWord(Base):
    __tablename__ = "daily_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_key: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    task_index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    word: Mapped[str] = mapped_column(String(5), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    games: Mapped[list[Game]] = relationship("Game", back_populates="daily_word")


class Game(Base):
    __tablename__ = "games"

    __table_args__ = (
        UniqueConstraint("player_id", "daily_word_id", name="uq_games_player_daily_word"),
        Index("ix_games_daily_word_status_finished", "daily_word_id", "status", "finished_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    daily_word_id: Mapped[int] = mapped_column(ForeignKey("daily_words.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    win_elapsed_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    win_attempt_no: Mapped[int | None] = mapped_column(Integer, nullable=True)

    player: Mapped[Player] = relationship("Player", back_populates="games")
    daily_word: Mapped[DailyWord] = relationship("DailyWord", back_populates="games")
    guesses: Mapped[list[Guess]] = relationship(
        "Guess", back_populates="game", cascade="all, delete-orphan", order_by="Guess.attempt_no"
    )
    share_link: Mapped[ShareLink | None] = relationship("ShareLink", back_populates="game", uselist=False)


class Guess(Base):
    __tablename__ = "guesses"

    __table_args__ = (
        UniqueConstraint("game_id", "attempt_no", name="uq_guesses_game_attempt"),
        Index("ix_guesses_game_attempt", "game_id", "attempt_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    guess_word: Mapped[str] = mapped_column(String(5), nullable=False)
    result_mask: Mapped[str] = mapped_column(String(5), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    game: Mapped[Game] = relationship("Game", back_populates="guesses")


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), unique=True, nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    game: Mapped[Game] = relationship("Game", back_populates="share_link")
