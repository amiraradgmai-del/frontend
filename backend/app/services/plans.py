from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.portal import UserSubscription


PACKAGE_MULTIPLIERS = {"silver": 1, "gold": 2, "diamond": 4}
PACKAGE_PRICES = {"silver": 1.0, "gold": 1.75, "diamond": 3.2}


def active_package(session: Session, user: User) -> str:
    if user.account_tier == "normal":
        return "silver"
    subscription = session.scalar(
        select(UserSubscription)
        .where(
            UserSubscription.user_id == user.id,
            UserSubscription.status == "active",
        )
        .order_by(UserSubscription.ends_at.desc())
    )
    return subscription.package_code if subscription else "silver"


def scaled_limits(session: Session, user: User, limits: dict[str, dict[str, int]]) -> dict[str, int]:
    base = limits.get(user.account_tier, limits["normal"])
    multiplier = PACKAGE_MULTIPLIERS[active_package(session, user)]
    return {key: value * multiplier for key, value in base.items()}


def package_price(base_price: int, package: str) -> int:
    return round(base_price * PACKAGE_PRICES[package] / 1000) * 1000
