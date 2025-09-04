from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from utils.logger import get_logger
import os
import tomli
import shutil
from packaging import version

MARICRAFT_VERSION = "0.3.0"

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


def _get_template_path() -> str:
    """获取模板文件路径"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "config-template.toml")
    
    if not os.path.exists(template_path):
        # 兼容从项目根目录执行
        template_path = os.path.join(os.getcwd(), "config-template.toml")
    
    return template_path


def _get_version_from_toml(toml_path: str) -> Optional[str]:
    """从TOML文件中获取版本号"""
    try:
        with open(toml_path, "rb") as f:
            data = tomli.load(f)
        return data.get("inner", {}).get("version")
    except Exception:
        return None


def _compare_versions(template_version: str, config_version: str) -> bool:
    """比较版本号，返回True表示模板版本更高"""
    try:
        return version.parse(template_version) > version.parse(config_version)
    except Exception:
        # 如果版本号格式不正确，认为需要更新
        return True


def _parse_toml_with_comments(file_path: str) -> tuple[Dict[str, Any], str]:
    """解析TOML文件并保留注释"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 使用tomli解析数据
    with open(file_path, "rb") as f:
        data = tomli.load(f)
    
    return data, content


def _update_config_from_template(config_path: str, template_path: str) -> None:
    """从模板更新配置文件，保留用户的自定义设置和注释"""
    logger = get_logger("ConfigLoader")
    
    try:
        # 读取模板和现有配置
        template_data, template_content = _parse_toml_with_comments(template_path)
        
        # 如果配置文件存在，读取现有配置
        existing_data = {}
        existing_content = ""
        if os.path.exists(config_path):
            existing_data, existing_content = _parse_toml_with_comments(config_path)
        
        # 创建备份
        if os.path.exists(config_path):
            backup_path = config_path + ".backup"
            shutil.copy2(config_path, backup_path)
            logger.info(f"[配置更新] 已创建备份文件: {backup_path}")
        
        # 合并配置：以模板为基础，保留用户的自定义值
        merged_data = {}
        
        # 首先添加模板中的所有配置项
        for section, values in template_data.items():
            if isinstance(values, dict):
                merged_data[section] = {}
                for key, template_value in values.items():
                    # 如果现有配置中有相同的键，且不是默认值，则保留用户设置
                    if (section in existing_data and 
                        key in existing_data[section] and 
                        existing_data[section][key] != template_value and
                        not (key == "api_key" and existing_data[section][key] == "your-api-key") and
                        not (section == "inner" and key == "version")):
                        merged_data[section][key] = existing_data[section][key]
                        logger.info(f"[配置更新] 保留用户设置: {section}.{key} = {existing_data[section][key]}")
                    else:
                        merged_data[section][key] = template_value
            else:
                merged_data[section] = values
        
        # 生成新的配置文件内容，保留注释
        new_content = _generate_config_content_with_comments(merged_data, template_content, existing_content)
        
        # 写入更新后的配置
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        logger.info(f"[配置更新] 配置文件已更新: {config_path}")
        
    except Exception as e:
        logger.error(f"[配置更新] 更新配置文件失败: {e}")
        raise


def _generate_config_content_with_comments(merged_data: Dict[str, Any], template_content: str, existing_content: str) -> str:
    """生成包含注释的配置文件内容"""
    lines = []
    
    # 添加文件头注释
    lines.append("# Maicraft插件配置")
    lines.append("")
    
    def _format_toml_value(value: Any) -> str:
        """将Python值转换为TOML字面量字符串，确保布尔为小写true/false。"""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"'
        if isinstance(value, (int, float)):
            return str(value)
        if value is None:
            return '""'
        if isinstance(value, list):
            items = ", ".join(_format_toml_value(v) for v in value)
            return f"[ {items} ]"
        return f'"{str(value)}"'
    
    # 为每个section生成内容
    for section, values in merged_data.items():
        # 添加section注释（从模板中提取）
        section_comment = _extract_section_comment(template_content, section)
        if section_comment:
            lines.append(section_comment)
        
        lines.append(f"[{section}]")
        
        if isinstance(values, dict):
            for key, value in values.items():
                # 添加key的注释（从模板中提取）
                key_comment = _extract_key_comment(template_content, section, key)
                if key_comment:
                    lines.append(key_comment)
                
                # 添加配置项
                lines.append(f'{key} = {_format_toml_value(value)}')
        else:
            lines.append(f'value = {_format_toml_value(values)}')
        
        lines.append("")
    
    return "\n".join(lines)


def _extract_section_comment(content: str, section: str) -> str:
    """从内容中提取section的注释"""
    lines = content.split('\n')
    section_line = f"[{section}]"
    
    for i, line in enumerate(lines):
        if line.strip() == section_line:
            # 查找section前的注释
            for j in range(i-1, -1, -1):
                comment_line = lines[j].strip()
                if comment_line.startswith('#'):
                    return comment_line
                elif comment_line == '':
                    continue
                else:
                    break
            break
    
    return ""


def _extract_key_comment(content: str, section: str, key: str) -> str:
    """从内容中提取key的注释"""
    lines = content.split('\n')
    in_section = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # 检查是否进入目标section
        if line_stripped == f"[{section}]":
            in_section = True
            continue
        
        # 如果遇到新的section，退出当前section
        if in_section and line_stripped.startswith('[') and line_stripped.endswith(']'):
            break
        
        # 在目标section中查找key
        if in_section and line_stripped.startswith(f'{key} ='):
            # 查找key前的注释
            for j in range(i-1, -1, -1):
                comment_line = lines[j].strip()
                if comment_line.startswith('#'):
                    return comment_line
                elif comment_line == '':
                    continue
                else:
                    break
            break
    
    return ""


def _create_default_config_toml(config_path: str) -> None:
    """从config-template.toml创建默认的config.toml文件"""
    logger = get_logger("ConfigLoader")
    
    try:
        template_path = _get_template_path()
        
        if not os.path.exists(template_path):
            logger.error("[配置创建] 未找到config-template.toml文件")
            raise FileNotFoundError("config-template.toml文件不存在")
        
        # 读取模板文件内容
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 创建config.toml文件
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(template_content)
        
        logger.info(f"[配置创建] 已从模板创建配置文件: {config_path}")
        
    except Exception as e:
        logger.error(f"[配置创建] 创建默认配置文件失败: {e}")
        raise


def _get_config_path() -> str:
    """获取配置文件路径，如果不存在则创建默认配置，如果版本过旧则更新"""
    logger = get_logger("ConfigLoader")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.toml")
    
    if not os.path.exists(config_path):
        # 兼容从项目根目录执行
        config_path = os.path.join(os.getcwd(), "config.toml")
    
    template_path = _get_template_path()
    
    if not os.path.exists(config_path):
        # 如果配置文件不存在，创建默认配置文件
        logger.info("[配置加载] 未找到config.toml文件，正在创建默认配置...")
        _create_default_config_toml(config_path)
    else:
        # 如果配置文件存在，检查版本是否需要更新
        try:
            template_version = _get_version_from_toml(template_path)
            config_version = _get_version_from_toml(config_path)
            
            if template_version and config_version:
                if _compare_versions(template_version, config_version):
                    logger.info(f"[配置更新] 检测到模板版本更新: {config_version} -> {template_version}")
                    _update_config_from_template(config_path, template_path)
                else:
                    logger.debug(f"[配置检查] 配置文件版本已是最新: {config_version}")
            else:
                logger.warning("[配置检查] 无法获取版本信息，跳过版本检查")
                
        except Exception as e:
            logger.warning(f"[配置检查] 版本检查失败: {e}")
    
    return config_path


# 加载配置
config_path = _get_config_path()
config_dict = _load_config_from_toml(config_path)
global_config = load_config_from_dict(config_dict)