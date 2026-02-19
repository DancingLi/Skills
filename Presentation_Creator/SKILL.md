---
name: "presentation-creator"
description: "根据用户提供的 Markdown 内容，自动生成 HTML+CSS 演示文稿。支持简单和复杂两种交互模式。"
---

# Presentation Creator 技能

## 功能说明

该技能根据用户提供的 Markdown 内容，自动生成美观的 HTML+CSS 演示文稿。支持两种交互模式：
- **简单模式**：基础的左右翻页
- **复杂模式**：支持键盘导航、全屏、进度条、演讲者模式等

## 使用方式

```bash
python "~\create_presentation.py" --input <markdown_file> --mode [simple|complex] --output <output_dir>
```

## 参数说明

| 参数 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `--input` | Markdown 输入文件路径 | 是 | - |
| `--mode` | 交互模式：simple（简单）或 complex（复杂） | 否 | simple |
| `--output` | 输出目录路径 | 否 | ./presentation |
| `--title` | 演示文稿标题 | 否 | Presentation |

## Markdown 格式要求

每个幻灯片用 `---` 分隔：

```markdown
# 第一页标题

内容...

---

# 第二页标题

- 列表项 1
- 列表项 2
```

## 输出

生成的演示文稿文件：
- `index.html` - 主 HTML 文件
- `styles.css` - 样式文件

