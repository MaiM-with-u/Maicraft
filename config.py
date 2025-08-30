from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from utils.logger import get_logger
import os
import tomli

class LoggingConfig(BaseModel):
    """Logging配置模型"""
    level: str = Field(default="INFO", description="日志级别")

class LLMConfig(BaseModel):
    """LLM配置模型"""

    model: str = Field(default="gpt-4o-mini", description="LLM模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
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
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="温度参数") 
    max_tokens: int = Field(default=1024, ge=100, le=8000, description="最大token数")
    
class Visual(BaseModel):
    """视觉模型配置模型"""
    enable: bool = Field(default=False, description="是否启用视觉模型")

class VLMConfig(BaseModel):
    """VLM配置模型"""
    model: str = Field(default="gpt-4o-mini", description="VLM模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="温度参数") 
    max_tokens: int = Field(default=1024, ge=100, le=8000, description="最大token数")

class AgentConfig(BaseModel):
    """Agent配置模型"""

    enabled: bool = Field(default=True, description="是否启用Agent")
    session_id: str = Field(default="maicraft_default", description="会话ID")
    max_steps: int = Field(default=50, ge=1, le=100, description="最大步骤数")
    tick_seconds: float = Field(default=8.0, ge=1.0, le=60.0, description="执行间隔(秒)")
    report_each_step: bool = Field(default=True, description="是否报告每个步骤")

    @field_validator("max_steps")
    @classmethod
    def validate_max_steps(cls, v):
        """验证最大步骤数"""
        if v > 100:
            raise ValueError("max_steps不能超过100")
        return v

    @field_validator("tick_seconds")
    @classmethod
    def validate_tick_seconds(cls, v):
        """验证执行间隔"""
        if v < 1.0 or v > 60.0:
            raise ValueError("tick_seconds必须在1.0到60.0之间")
        return v





class MaicraftConfig(BaseModel):
    """Maicraft插件配置模型"""

    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging配置")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")
    llm_fast: LLMConfigFast = Field(default_factory=LLMConfigFast, description="LLM快速配置")
    visual: Visual = Field(default_factory=Visual, description="视觉模型配置")
    vlm: VLMConfig = Field(default_factory=VLMConfig, description="VLM配置")
    agent: AgentConfig = Field(default_factory=AgentConfig, description="Agent配置")

    # 注意：无 agent_mode 字段，移除对应校验器以避免 Pydantic 报错

    @field_validator("agent")
    @classmethod
    def validate_agent_config(cls, v):
        """验证Agent配置"""
        if v.max_steps > 100:
            raise ValueError("max_steps不能超过100")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        try:
            # pydantic v2
            return self.model_dump()
        except AttributeError:
            # 兼容 pydantic v1
            return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaicraftConfig":
        """从字典创建配置"""
        return cls(**data)

    def validate_and_log(self) -> bool:
        """验证配置并记录日志"""
        logger = get_logger("MaicraftConfig")
        try:
            # pydantic v2 在实例化时已验证；通过序列化再次触发潜在校验
            _ = self.to_dict()
            logger.info("[配置验证] 配置验证通过")

            # 记录配置信息
            logger.info(f"[配置验证] LLM模型: {self.llm.model}")
            logger.info(f"[配置验证] Agent启用: {self.agent.enabled}")
            logger.info(f"[配置验证] 最大步骤: {self.agent.max_steps}")
            logger.info(f"[配置验证] 执行间隔: {self.agent.tick_seconds}秒")

            return True

        except Exception as e:
            logger.error(f"[配置验证] 配置验证失败: {e}")
            return False


def load_config_from_dict(config_data: Dict[str, Any]) -> MaicraftConfig:
    """从字典加载配置"""
    logger = get_logger("ConfigLoader")
    try:
        config = MaicraftConfig.from_dict(config_data)
        if config.validate_and_log():
            logger.info("[配置加载] 配置加载成功")
            return config
        else:
            raise ValueError("配置验证失败")
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