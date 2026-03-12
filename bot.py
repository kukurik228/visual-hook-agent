import os
import json
import asyncio
import httpx
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

KNOWLEDGE = """
ТЫ — эксперт по созданию визуальных хуков для первых 3 секунд 2D-анимационных роликов.
Твой стиль: гибрид Kurzgesagt + Vox + YouTube thumbnail psychology.

КОНТЕКСТ:
- Познавательные ролики (психология, бизнес, путешествия и разное)
- Формат: 2D анимация
- Задача хука: за 3 секунды БЕЗ звука вызвать вопрос, на который зритель хочет получить ответ
- Хук НЕ раскрывает ответ — только создаёт напряжение и интерес
- Главная боль: придумать оригинальную, неочевидную идею

PRIMARY HOOK SYSTEMS (использовать всегда)

ПСИХОЛОГИЯ ПРЕВЬЮ:
Трёхэтапная модель клика (1-2 секунды):
1. Visual Stun Gun — резкий паттерн-интерраптор, парализует скроллинг
2. Title Value Hunting — зритель ищет "что мне с этого"
3. Visual Validation — изображение подтверждает обещание, создаёт доверие

Curiosity Gap:
- До/После: невероятный контраст между точкой А и точкой Б
- Вызов: момент перед критическим событием — мозг хочет увидеть исход
- Противоречие: нарушение ожиданий создаёт ментальный зуд
- Новизна: странный объект в привычном контексте
- Результат: финал без объяснения процесса

25 ТИПОВ ХУКОВ:
1. Момент перед катастрофой — кадр за секунду до события
2. Невозможное действие — физически невозможное
3. Парадокс объекта — предмет не соответствует своей функции
4. Огромный масштаб — нарушение привычных пропорций
5. Микромир — невидимое обычному глазу
6. Визуальный вопрос — кадр вызывает мгновенный вопрос
7. Трансформация — начало в момент превращения
8. Неожиданный результат — ожидаем одно, происходит другое
9. Разрушение — что-то ломается или падает
10. Визуальный контраст — два противоположных объекта
11. Объект в неправильном месте
12. Кнопка / рычаг — мозг обожает интерактивность
13. Разрез объекта — показывается внутренность
14. Визуальная загадка — непонятный объект
15. Неожиданный масштаб времени — очень быстро/медленно
16. Иллюзия — кадр сначала кажется одним, потом другим
17. Объект на грани — висит над пропастью
18. Механизм — шестерни, цепные реакции
19. Домино-эффект — цепная реакция
20. Огромное число — визуализация масштаба
21. Визуальная метафора — абстракция превращается в объект
22. Появление из ничего — объект возникает в кадре
23. Нарушение гравитации
24. Большая угроза — опасность в кадре
25. Взгляд персонажа — реакция на что-то ужасное за кадром

БИБЛИОТЕКА ВИЗУАЛЬНЫХ МЕТАФОР:
рост / прогресс → ракета, лестница уходящая вверх, дерево пробивающее потолок
время → песочные часы, тающий куб льда, циферблат с ускоряющимися стрелками
стресс / давление → фигурка под огромным прессом, трескающееся стекло, пружина до предела
принятие решений → развилка дорог, весы, дверь с двумя замками
страх → тень поглощающая фигуру, фигурка на краю обрыва в темноте
манипуляция / контроль → марионетка на нитях, кнопки управления над чужой головой
одиночество → фигурка в центре пустого огромного пространства
здоровье → шкала заряда батареи вместо тела
привычка / петля → змея кусающая себя за хвост, замкнутый круг дорог
успех / провал → лестница вверх vs лестница вниз, две чаши весов

SECONDARY HOOK SYSTEM — MrBeast Style (вторичная, использовать умеренно):
Правило зон — итого всегда 10 хуков:
КРАСНАЯ (эмоция/концепт/психология) → 0 MrBeast + 10 основных
СЕРАЯ (физический объект, но нет числа/сравнения) → 1 MrBeast + 9 основных
ЗЕЛЁНАЯ (число/сравнение/челлендж/масштаб) → 2 MrBeast + 8 основных

5 MrBeast-техник для 2D анимации:
MB-1. Giant Object — крошечный персонаж рядом с огромным тематическим объектом
MB-2. Before Disaster — кадр за секунду до разрушения
MB-3. Massive Quantity — 1000 объектов заполняют экран
MB-4. Split Reality — экран разделён: лево vs право / до vs после
MB-5. Mystery Box — объект начинает открываться

ПРАВИЛА ТЕКСТА (тема всегда показывается в начале):
- Текст в ЛЕВОЙ части кадра, НИКОГДА в правом нижнем углу
- Тренд 2026: текст встроен В сцену — за объектом, взаимодействует с тенями
- Sans-Serif шрифты (Montserrat, Bebas), жирные
- Тень/обводка/свечение — текст должен читаться на любом фоне
- Ключевое слово — жёлтый или золотой, остальное — белый
- В composition ВСЕГДА указывать: где текст, как встроен, цвет+эффект
"""

def make_prompt(batch_num: int, scenario: str, used_ideas: list[str]) -> str:
    used_note = ""
    if used_ideas:
        used_note = "\n\nУЖЕ ИСПОЛЬЗОВАННЫЕ ИДЕИ — НЕ ПОВТОРЯТЬ:\n" + "\n".join(
            f"{i+1}. {idea}" for i, idea in enumerate(used_ideas)
        )

    mb_rule = (
        "В этой партии из 5: если зелёная зона — добавь 1 MrBeast хук, если серая — 1 MrBeast, если красная — 0."
        if batch_num == 1
        else "В этой партии из 5: если зелёная зона — добавь 1 MrBeast хук (второй и последний), иначе — 0."
    )

    return f"""{KNOWLEDGE}

СЦЕНАРИЙ:
{scenario}
{used_note}

Придумай 5 визуальных хуков (партия {batch_num} из 2). Хуки ПРЯМО связаны с темой. 2D анимация.

{mb_rule}
MrBeast-хуки: type = "MrBeast: [название]".

Используй БИБЛИОТЕКУ ВИЗУАЛЬНЫХ МЕТАФОР для абстрактных тем.

ТОЛЬКО валидный JSON, без markdown:
{{"hooks":[{{"type":"...","preview":"...","scene":"...","timeline":[{{"time":"0–1 сек","action":"..."}},{{"time":"1–2 сек","action":"..."}},{{"time":"2–3 сек","action":"..."}}],"composition":"...","text_on_screen":"...","progressive":"...","why":"..."}}]}}"""


async def call_anthropic(prompt: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 7000,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        data = response.json()
        raw = "".join(b.get("text", "") for b in data.get("content", []))

        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            raise ValueError("Не удалось распарсить ответ")
        parsed = json.loads(match.group())
        return parsed.get("hooks", [])


def format_hook(num: int, hook: dict) -> str:
    timeline = "\n".join(
        f"  {t['time']}: {t['action']}"
        for t in hook.get("timeline", [])
    )
    progressive = hook.get("progressive", "нет")
    text_on_screen = hook.get("text_on_screen", "нет")

    has_progressive = progressive.lower() not in ("нет", "no", "")
    has_text = text_on_screen.lower() not in ("нет", "no", "")

    lines = [
        f"*#{num} · {hook.get('type', '')}*",
        f"_{hook.get('preview', '')}_",
        "",
        f"📽 *Сцена:* {hook.get('scene', '')}",
        "",
        f"⏱ *Таймлайн:*\n{timeline}",
        "",
        f"🎬 *Композиция:* {hook.get('composition', '')}",
    ]

    if has_text:
        lines.append(f"✏️ *Текст:* {text_on_screen}")
    if has_progressive:
        lines.append(f"🔄 *Поступательно:* {progressive}")

    lines += ["", f"💡 _{hook.get('why', '')}_"]
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Visual Hook Agent*\n\n"
        "Отправь мне сценарий или тему ролика — я предложу 10 визуальных хуков для первых 3 секунд.\n\n"
        "Просто напиши тему или вставь сценарий 👇",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scenario = update.message.text.strip()
    if not scenario:
        return

    # Save scenario and reset state
    context.user_data["scenario"] = scenario
    context.user_data["used_ideas"] = []
    context.user_data["total_count"] = 0

    msg = await update.message.reply_text("⏳ Генерирую хуки 1–5...")

    try:
        batch1 = await call_anthropic(make_prompt(1, scenario, []))
        batch1_previews = [h.get("preview", "") for h in batch1]

        await msg.edit_text("⏳ Генерирую хуки 6–10...")

        batch2 = await call_anthropic(make_prompt(2, scenario, batch1_previews))
        hooks = batch1 + batch2

        context.user_data["used_ideas"] = [h.get("preview", "") for h in hooks]
        context.user_data["total_count"] = len(hooks)

        await msg.delete()
        await send_hooks(update, context, hooks, offset=0)

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}\nПопробуй ещё раз.")


async def send_hooks(update: Update, context: ContextTypes.DEFAULT_TYPE, hooks: list, offset: int):
    chat_id = update.effective_chat.id

    for i, hook in enumerate(hooks):
        text = format_hook(offset + i + 1, hook)
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        await asyncio.sleep(0.3)

    # Button "10 more"
    keyboard = [[InlineKeyboardButton("➕ Ещё 10 хуков", callback_data="more")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Готово — {context.user_data.get('total_count', len(hooks))} хуков сгенерировано",
        reply_markup=reply_markup,
    )


async def handle_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    scenario = context.user_data.get("scenario")
    if not scenario:
        await query.message.reply_text("Отправь сценарий заново — сессия устарела.")
        return

    used_ideas = context.user_data.get("used_ideas", [])
    total = context.user_data.get("total_count", 0)

    msg = await query.message.reply_text("⏳ Генерирую ещё хуки 1–5...")

    try:
        batch1 = await call_anthropic(make_prompt(1, scenario, used_ideas))
        batch1_previews = [h.get("preview", "") for h in batch1]

        await msg.edit_text("⏳ Генерирую ещё хуки 6–10...")

        batch2 = await call_anthropic(make_prompt(2, scenario, used_ideas + batch1_previews))
        hooks = batch1 + batch2

        context.user_data["used_ideas"] = used_ideas + [h.get("preview", "") for h in hooks]
        context.user_data["total_count"] = total + len(hooks)

        await msg.delete()
        await send_hooks(update, context, hooks, offset=total)

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}\nПопробуй ещё раз.")


def main():
    # Wait for previous instance to stop
    time.sleep(5)
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_more, pattern="^more$"))
    app.run_polling()


if __name__ == "__main__":
    main()
