# 知识管理器 (Knowledge Manager)

知识管理器是一个用于管理Minecraft相关知识的系统，支持通过分类和关键词两种方式组织和检索知识。

## 功能特性

### 1. 知识存储
- 支持按分类组织知识
- 每个知识项包含内容、分类和关键词
- 支持同一分类下存储多个知识项

### 2. 知识检索
- **按分类检索**: `get_knowledge_by_category(category)` - 获取指定分类下的所有知识
- **按关键词检索**: `get_knowledge_by_keywords(keywords)` - 获取包含指定关键词的所有知识
- **混合搜索**: `search_knowledge(query)` - 支持分类、关键词和内容的模糊搜索

### 3. 知识管理
- 添加知识: `add_knowledge(knowledge, category, keywords)`
- 删除知识: `remove_knowledge(category, knowledge_index)`
- 统计信息: `get_knowledge_count()`, `get_all_categories()`

## 使用示例

### 基本使用

```python
from knowledge_manager import KnowledgeManager

# 创建知识管理器
km = KnowledgeManager()

# 添加知识
km.add_knowledge(
    knowledge="钻石是最珍贵的矿物，可以制作高级工具",
    category="矿物",
    keywords=["钻石", "珍贵", "工具"]
)

# 通过分类获取知识
mineral_knowledge = km.get_knowledge_by_category("矿物")

# 通过关键词获取知识
diamond_knowledge = km.get_knowledge_by_keywords(["钻石"])

# 混合搜索
search_results = km.search_knowledge("工具")
```

### 高级功能

```python
# 获取统计信息
total_count = km.get_knowledge_count()
categories = km.get_all_categories()

# 删除特定知识
km.remove_knowledge("矿物", 0)  # 删除第一个矿物知识

# 删除整个分类
km.remove_knowledge("矿物")  # 删除所有矿物知识
```

## 数据结构

每个知识项的结构如下：

```python
{
    "knowledge": "知识内容",
    "category": "知识分类",
    "keywords": ["关键词1", "关键词2", "关键词3"]
}
```

## 搜索算法

### 关键词匹配
- 支持部分匹配（不区分大小写）
- 只要搜索关键词与知识项的关键词有交集即可匹配
- 支持多个关键词同时搜索

### 分类匹配
- 支持分类名称的部分匹配
- 不区分大小写

### 内容匹配
- 支持知识内容的模糊搜索
- 不区分大小写

## 测试

运行测试文件来验证功能：

```bash
cd src/plugins/maicraft/agent/knowledge
python test_knowledge_manager.py
```

测试将演示：
- 添加不同类型的知识
- 通过分类检索知识
- 通过关键词检索知识
- 混合搜索功能
- 删除知识功能

## 扩展建议

1. **持久化存储**: 添加数据库或文件存储支持
2. **权重系统**: 为关键词添加权重，提高搜索精度
3. **模糊匹配**: 支持拼写错误和相似词匹配
4. **知识图谱**: 建立知识项之间的关联关系
5. **版本控制**: 支持知识的版本管理和回滚
