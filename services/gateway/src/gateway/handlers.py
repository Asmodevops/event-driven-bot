"""Роутер gateway: тонкая обёртка над слоем application.

Хэндлеры здесь только цепляются к событиям aiogram и зовут интерактор; разбор
апдейта и публикация живут в ``gateway.application``.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message, Update
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from gateway.application import ProcessCallback, ProcessMessage


router = Router()


@router.message(CommandStart())
@inject
async def on_start(
    message: Message,
    event_update: Update,
    process_message: FromDishka[ProcessMessage],
) -> None:
    # event_update прокидывает aiogram — из него берём update_id.
    await process_message(event_update.update_id, message)


@router.callback_query()
@inject
async def on_callback(
    callback: CallbackQuery,
    event_update: Update,
    process_callback: FromDishka[ProcessCallback],
) -> None:
    await process_callback(event_update.update_id, callback)
