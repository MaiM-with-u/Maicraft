from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from utils.logger import get_logger
import os
import tomli

class LoggingConfig(BaseModel):
    """Logging配置模型"""
    level: str = Field(default="INFO", description="日志级别")
    
class BotConfig(BaseModel):
    player_name: str = Field(default="Mai", description="玩家名称")
    bot_name: str = Field(default="麦麦", description="机器人名称")

class GameConfig(BaseModel):
    goal: str = Field(default="以合适的步骤，建立营地，挖到16个钻石，并存储", description="游戏目标")

class LLMConfig(BaseModel):
    """LLM配置模型"""

    model: str = Field(default="gpt-4o-mini", description="LLM模型名称")
    api_key: str = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="温度参数") 
    max_tokens: int = Field(default=1024, ge=100, le=8000, description="最大token数")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        """验证温度参数"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("温度参数必须在0.0到2.0之间")
        return v

class LLMConfigFast(BaseModel):
    """LLM配置模型"""
    model: str = Field(default="gpt-4o-mini", description="LLM模型名称")
    api_key: str = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="温度参数") 
    max_tokens: int = Field(default=1024, ge=100, le=8000, description="最大token数")
    
class Visual(BaseModel):
    """视觉模型配置模型"""
    enable: bool = Field(default=False, description="是否启用视觉模型")

class VLMConfig(BaseModel):
    """VLM配置模型"""
    model: str = Field(default="gpt-4o-mini", description="VLM模型名称")
    api_key: str = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="温度参数") 
    max_tokens: int = Field(default=1024, ge=100, le=8000, description="最大token数")




class MaicraftConfig(BaseModel):
    """Maicraft插件配置模型"""

    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging配置")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")
    llm_fast: LLMConfigFast = Field(default_factory=LLMConfigFast, description="LLM快速配置")
    visual: Visual = Field(default_factory=Visual, description="视觉模型配置")
    vlm: VLMConfig = Field(default_factory=VLMConfig, description="VLM配置")
    bot: BotConfig = Field(default_factory=BotConfig, description="Bot配置")
    game: GameConfig = Field(default_factory=GameConfig, description="Game配置")

    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> "MaicraftConfig":
        """从字典创建配置对象
        
        Args:
            config_data: 配置字典数据
            
        Returns:
            MaicraftConfig: 配置对象实例
        """
        # 使用 Pydantic 的 model_validate 方法（Pydantic v2）
        # 如果使用 Pydantic v1，可以替换为 parse_obj
        try:
            return cls.model_validate(config_data)
        except AttributeError:
            # 兼容 Pydantic v1
            return cls.parse_obj(config_data)


def load_config_from_dict(config_data: Dict[str, Any]) -> MaicraftConfig:
    """从字典加载配置"""
    logger = get_logger("ConfigLoader")
    try:
        config = MaicraftConfig.from_dict(config_data)
        logger.info("[配置加载] 配置加载成功")
        return config
    except Exception as e:
        logger.error(f"[配置加载] 配置加载失败: {e}")
        raise


def create_default_config() -> MaicraftConfig:
    """创建默认配置"""
    return MaicraftConfig()


def _load_config_from_toml(toml_path: str) -> Dict[str, Any]:
    with open(toml_path, "rb") as f:
        data = tomli.load(f)
    return data

base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "config.toml")
if not os.path.exists(config_path):
    # 兼容从项目根目录执行
    config_path = os.path.join(os.getcwd(), "config.toml")

config_dict = _load_config_from_toml(config_path)
global_config = load_config_from_dict(config_dict)