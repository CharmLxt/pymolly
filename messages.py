"""Шаблоны сообщений Молли и фразы поддержки."""
import random


STANDARD_TEMPLATE = (
    "Молли обнаружила ошибку {type}. "
    "Она означает: {description} "
    "Возможно, её появление связано с: {cause}. "
    "Чтобы починить ошибку, попробуйте: {suggestion}."
)

RESOLVED_MESSAGE = "Молли не обнаружила прошлой ошибки, работа может идти дальше!"

WAFF_INTRO_TEMPLATE = (
    "Молли столкнулась с ошибкой {type}. "
    "Она означает: {description} "
    "Молли хочет вам помочь с помощью: {fix_description}."
)

WAFF_FIXING_TEMPLATE = "Молли начинает починку {fix_name}..."
WAFF_SUCCESS_TEMPLATE = "Молли успешно починила {fix_name}, можете продолжать работу!"
WAFF_FAILURE_TEMPLATE = (
    "К сожалению, Молли не удалось выполнить {fix_name} и починить {problem}. "
    "Возможно, проблема кроется глубже или в чём-то другом."
)
WAFF_SUGGEST_TEMPLATE = "Попробуйте выполнить: {alternative}."

ENCOURAGEMENTS = [
    "Молли верит, что у вас всё обязательно получится!",
    "Молли держит за вас кулачки!",
    "Не сдавайтесь, у вас всё получится!",
    "Молли рядом и всегда готова помочь!",
    "Вы справитесь, Молли в вас верит!",
]


def get_encouragement():
    return random.choice(ENCOURAGEMENTS)


def build_standard_message(info, randomize=True):
    causes = info.get("causes") or ["неизвестной причиной"]
    suggestions = info.get("suggestions") or ["перезапустить код"]

    cause = random.choice(causes) if randomize else causes[0]
    suggestion = random.choice(suggestions) if randomize else suggestions[0]

    return STANDARD_TEMPLATE.format(
        type=info["type"],
        description=info["description"],
        cause=cause,
        suggestion=suggestion,
    )


__all__ = [
    "STANDARD_TEMPLATE", "RESOLVED_MESSAGE",
    "WAFF_INTRO_TEMPLATE", "WAFF_FIXING_TEMPLATE",
    "WAFF_SUCCESS_TEMPLATE", "WAFF_FAILURE_TEMPLATE", "WAFF_SUGGEST_TEMPLATE",
    "ENCOURAGEMENTS", "get_encouragement", "build_standard_message",
]