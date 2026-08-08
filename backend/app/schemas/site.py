from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ThemeSettings(BaseModel):
    primary_color: str = "#2563eb"
    accent_color: str = "#f97316"
    background_color: str = "#fffaf5"
    font_family: Literal["Vazirmatn", "Tahoma", "Arial", "serif"] = "Vazirmatn"
    border_radius: int = Field(default=14, ge=6, le=28)

    @field_validator("primary_color", "accent_color", "background_color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("Color must be a six-digit hex value")
        int(value[1:], 16)
        return value.lower()


class BrandingSettings(BaseModel):
    site_name: str = Field(default="چکاه", min_length=2, max_length=80)
    short_description: str = Field(
        default="دستیار هوشمند و همراه مالیاتی شما", max_length=180
    )
    logo_url: str = Field(default="/brand/chakah-logo.png", max_length=500)
    support_email: str = Field(default="", max_length=320)
    support_phone: str = Field(default="", max_length=30)
    support_mobile: str = Field(default="", max_length=30)
    office_address: str = Field(default="", max_length=500)
    working_hours: str = Field(default="", max_length=180)
    legal_name: str = Field(default="", max_length=160)
    map_url: str = Field(default="", max_length=500)
    instagram_url: str = Field(default="", max_length=500)
    whatsapp_url: str = Field(default="", max_length=500)
    telegram_url: str = Field(default="", max_length=500)


class SeoSettings(BaseModel):
    default_title: str = Field(default="چکاه | دستیار هوشمند مالیاتی", max_length=70)
    default_description: str = Field(
        default="پاسخ ساده، دقیق و هوشمند به پرسش‌های مالیاتی ایران", max_length=170
    )
    keywords: str = Field(default="مالیات، قوانین مالیاتی، دستیار مالیاتی، مشاور مالیاتی", max_length=300)


class FeatureSettings(BaseModel):
    maintenance_mode: bool = False
    registration_enabled: bool = True
    chatbot_enabled: bool = True
    consultations_enabled: bool = True


class AiPolicySettings(BaseModel):
    generation_model: Literal[
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-3.5-flash",
    ] = "gemini-2.5-flash"
    general_knowledge_enabled: bool = True
    general_knowledge_weight: int = Field(default=20, ge=0, le=40)
    casual_chat_enabled: bool = True
    require_sources_for_sensitive_answers: bool = True
    monthly_api_budget_toman: int = Field(default=5_000_000, ge=100_000, le=1_000_000_000)
    estimated_cost_per_message_toman: int = Field(default=350, ge=1, le=100_000)


class SiteConfigPayload(BaseModel):
    theme: ThemeSettings = Field(default_factory=ThemeSettings)
    branding: BrandingSettings = Field(default_factory=BrandingSettings)
    seo: SeoSettings = Field(default_factory=SeoSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)
    ai_policy: AiPolicySettings = Field(default_factory=AiPolicySettings)


class SiteDraftUpdate(BaseModel):
    configuration: SiteConfigPayload


class SitePublishRequest(BaseModel):
    note: str = Field(default="", max_length=300)


class SiteRollbackRequest(BaseModel):
    version: int = Field(ge=1)
    note: str = Field(default="بازگشت به نسخه قبلی", max_length=300)
