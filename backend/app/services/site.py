from sqlalchemy.orm import Session

from app.models.site import SiteConfiguration
from app.schemas.site import AiPolicySettings


def feature_enabled(session: Session, feature: str, default: bool = True) -> bool:
    configuration = session.get(SiteConfiguration, 1)
    if configuration is None:
        return default
    features = configuration.published_json.get("features", {})
    return bool(features.get(feature, default))


def get_ai_policy(session: Session) -> AiPolicySettings:
    configuration = session.get(SiteConfiguration, 1)
    if configuration is None:
        return AiPolicySettings()
    return AiPolicySettings.model_validate(
        configuration.published_json.get("ai_policy", {})
    )
