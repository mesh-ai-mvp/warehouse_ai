"""Configuration management for AI agents"""

import configparser
import os
from typing import Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class AIConfig(BaseModel):
    """AI Agent configuration model"""

    # OpenAI settings
    openai_api_key: str = Field(default="")
    model_name: str = Field(default="gpt-5-mini")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    request_timeout: int = Field(default=30)

    # Forecast agent settings
    forecast_lookback_days: int = Field(default=30)
    forecast_horizon_months: int = Field(default=3)

    # Adjustment agent settings
    adjustment_factors_enabled: bool = Field(default=True)
    seasonal_adjustments: Dict[str, float] = Field(default_factory=dict)
    flu_season_months: list = Field(default_factory=list)
    flu_season_multiplier: float = Field(default=1.2)
    holiday_reduction: float = Field(default=0.9)
    summer_reduction: float = Field(default=0.85)

    # Supplier agent settings
    supplier_scoring_weights: Dict[str, float] = Field(default_factory=dict)
    max_lead_time_days: int = Field(default=14)
    preferred_status: str = Field(default="OK")
    min_supplier_score: float = Field(default=0.6)
    enable_order_splitting: bool = Field(default=True)
    max_suppliers_per_order: int = Field(default=3)

    # Cache settings
    enable_cache: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=300)

    # API settings
    max_requests_per_minute: int = Field(default=60)
    retry_attempts: int = Field(default=3)
    retry_delay_seconds: int = Field(default=2)

    # UI settings
    show_reasoning: bool = Field(default=True)
    show_confidence_scores: bool = Field(default=True)
    enable_manual_override: bool = Field(default=True)


class ConfigLoader:
    """Loads and manages configuration from multiple sources"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/config.ini"
        self.config = self._load_config()

    def _load_config(self) -> AIConfig:
        """Load configuration from file and environment"""
        config_data = {}

        # Load from config.ini if it exists
        if os.path.exists(self.config_path):
            parser = configparser.ConfigParser()
            parser.read(self.config_path)

            # AI agent settings
            if "ai_agents" in parser:
                ai_section = parser["ai_agents"]
                config_data["model_name"] = ai_section.get("model_name", "gpt-5-mini")
                config_data["temperature"] = float(ai_section.get("temperature", 0.7))
                config_data["max_tokens"] = int(ai_section.get("max_tokens", 2000))
                config_data["request_timeout"] = int(
                    ai_section.get("request_timeout", 30)
                )
                config_data["forecast_lookback_days"] = int(
                    ai_section.get("forecast_lookback_days", 30)
                )
                config_data["forecast_horizon_months"] = int(
                    ai_section.get("forecast_horizon_months", 3)
                )
                config_data["adjustment_factors_enabled"] = ai_section.getboolean(
                    "adjustment_factors_enabled", True
                )

                # Parse supplier scoring weights
                weights_str = ai_section.get(
                    "supplier_scoring_weights", "price:0.4,lead_time:0.3,status:0.3"
                )
                weights = {}
                for item in weights_str.split(","):
                    key, value = item.split(":")
                    weights[key] = float(value)
                config_data["supplier_scoring_weights"] = weights

            # Seasonal adjustments
            if "seasonal_adjustments" in parser:
                seasonal = {}
                for month, value in parser["seasonal_adjustments"].items():
                    seasonal[month] = float(value)
                config_data["seasonal_adjustments"] = seasonal

            # Event adjustments
            if "event_adjustments" in parser:
                event_section = parser["event_adjustments"]
                flu_months_str = event_section.get(
                    "flu_season_months", "10,11,12,1,2,3"
                )
                config_data["flu_season_months"] = [
                    int(m) for m in flu_months_str.split(",")
                ]
                config_data["flu_season_multiplier"] = float(
                    event_section.get("flu_season_multiplier", 1.2)
                )
                config_data["holiday_reduction"] = float(
                    event_section.get("holiday_reduction", 0.9)
                )
                config_data["summer_reduction"] = float(
                    event_section.get("summer_reduction", 0.85)
                )

            # Supplier preferences
            if "supplier_preferences" in parser:
                supplier_section = parser["supplier_preferences"]
                config_data["max_lead_time_days"] = int(
                    supplier_section.get("max_lead_time_days", 14)
                )
                config_data["preferred_status"] = supplier_section.get(
                    "preferred_status", "OK"
                )
                config_data["min_supplier_score"] = float(
                    supplier_section.get("min_supplier_score", 0.6)
                )
                config_data["enable_order_splitting"] = supplier_section.getboolean(
                    "enable_order_splitting", True
                )
                config_data["max_suppliers_per_order"] = int(
                    supplier_section.get("max_suppliers_per_order", 3)
                )

            # Cache settings
            if "cache" in parser:
                cache_section = parser["cache"]
                config_data["enable_cache"] = cache_section.getboolean(
                    "enable_cache", True
                )
                config_data["cache_ttl_seconds"] = int(
                    cache_section.get("cache_ttl_seconds", 300)
                )

            # API settings
            if "api" in parser:
                api_section = parser["api"]
                config_data["max_requests_per_minute"] = int(
                    api_section.get("max_requests_per_minute", 60)
                )
                config_data["retry_attempts"] = int(
                    api_section.get("retry_attempts", 3)
                )
                config_data["retry_delay_seconds"] = int(
                    api_section.get("retry_delay_seconds", 2)
                )

            # UI settings
            if "ui" in parser:
                ui_section = parser["ui"]
                config_data["show_reasoning"] = ui_section.getboolean(
                    "show_reasoning", True
                )
                config_data["show_confidence_scores"] = ui_section.getboolean(
                    "show_confidence_scores", True
                )
                config_data["enable_manual_override"] = ui_section.getboolean(
                    "enable_manual_override", True
                )

        # Override with environment variables
        config_data["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")

        return AIConfig(**config_data)

    def get_config(self) -> AIConfig:
        """Get the loaded configuration"""
        return self.config

    def reload(self):
        """Reload configuration from sources"""
        self.config = self._load_config()


# Global configuration instance
_config_loader = None


def get_config() -> AIConfig:
    """Get the global configuration instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.get_config()


def reload_config():
    """Reload the global configuration"""
    global _config_loader
    if _config_loader:
        _config_loader.reload()
