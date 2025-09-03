"""
Prompt Manager - 智能提示词模板管理器

提供模板注册、参数格式化和提示词生成功能，支持结构化参数和动态内容生成。
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging


@dataclass
class PromptTemplate:
    """提示词模板类"""
    name: str
    template: str
    description: str = ""
    parameters: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后自动提取参数"""
        if not self.parameters:
            self.parameters = self._extract_parameters()
    
    def _extract_parameters(self) -> List[str]:
        """从模板中提取参数名"""
        param_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)(?::[^}]+)?\}'
        params = re.findall(param_pattern, self.template)
        return list(set(params))
    
    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """验证提供的参数是否完整"""
        missing_params = []
        for param in self.parameters:
            if param not in params:
                missing_params.append(param)
        return missing_params
    
    def format(self, **kwargs) -> str:
        """格式化模板"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            missing_param = str(e).strip("'")
            raise ValueError(f"缺少必需参数: {missing_param}")
        except Exception as e:
            raise ValueError(f"模板格式化失败: {e}")


class PromptManager:
    """提示词管理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.templates: Dict[str, PromptTemplate] = {}
        self.logger = logger or logging.getLogger(__name__)
    
    def register_template(self, template: PromptTemplate) -> bool:
        """注册新模板"""
        try:
            if template.name in self.templates:
                self.logger.warning(f"模板 '{template.name}' 已存在，将被覆盖")
            
            self.templates[template.name] = template
            self.logger.info(f"成功注册模板: {template.name}")
            return True
        except Exception as e:
            self.logger.error(f"注册模板失败: {e}")
            return False
    
    def register_template_from_string(self, name: str, template_str: str, description: str = "") -> bool:
        """从字符串注册模板"""
        try:
            template = PromptTemplate(
                name=name,
                template=template_str,
                description=description,
            )
            return self.register_template(template)
        except Exception as e:
            self.logger.error(f"从字符串注册模板失败: {e}")
            return False
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """获取指定名称的模板"""
        return self.templates.get(name)
    
    def generate_prompt(self, template_name: str, **kwargs) -> str:
        """根据模板名称和参数生成提示词"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"模板 '{template_name}' 不存在")
        
        # 验证参数
        missing_params = template.validate_parameters(kwargs)
        if missing_params:
            raise ValueError(f"缺少必需参数: {', '.join(missing_params)}")
        
        # 格式化模板
        try:
            result = template.format(**kwargs)
            self.logger.debug(f"成功生成提示词，模板: {template_name}")
            return result
        except Exception as e:
            self.logger.error(f"生成提示词失败: {e}")
            raise

prompt_manager = PromptManager()

# 便捷函数
def create_prompt_manager(logger: Optional[logging.Logger] = None) -> PromptManager:
    """创建提示词管理器的便捷函数"""
    return PromptManager(logger)


def quick_generate(template_str: str, **kwargs) -> str:
    """快速生成提示词（无需注册模板）"""
    template = PromptTemplate(
        name="quick",
        template=template_str
    )
    return template.format(**kwargs)
