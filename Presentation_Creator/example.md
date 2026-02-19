# Presentation Creator

使用 Markdown 快速创建美观的 HTML+CSS 演示文稿

---

## 功能特点

- **简单易用**：只需编写 Markdown
- **两种模式**：简单模式和复杂模式
- **美观样式**：现代化紫色主题
- **无需依赖**：纯 HTML+CSS+JavaScript

---

## 使用方法

```bash
python create_presentation.py \
    --input example.md \
    --mode complex \
    --output ./my-presentation
```

---

## Markdown 格式

每个幻灯片用 `---` 分隔：

```markdown
# 第一页

内容...

---

# 第二页

更多内容...
```

---

## 支持的格式

- 标题（H1-H3）
- 段落
- 列表（有序/无序）
- 代码块
- 引用
- 表格

---

## 代码示例

```python
def hello():
    print("Hello, World!")
```

---

## 引用

> 这是一个引用块
> 可以包含多行内容

---

## 表格示例

| 功能 | 简单模式 | 复杂模式 |
|------|---------|---------|
| 翻页按钮 | ✅ | ✅ |
| 键盘导航 | ❌ | ✅ |
| 进度条 | ❌ | ✅ |
| 全屏 | ❌ | ✅ |
| 页码 | ❌ | ✅ |

---

## 快捷键（复杂模式）

- `←` 或 `PageUp`：上一页
- `→`、`PageDown` 或 `空格`：下一页
- `F`：全屏切换

---

## 谢谢观看

感谢使用 Presentation Creator！
