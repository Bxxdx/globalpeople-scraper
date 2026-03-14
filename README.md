# 环球人物网新闻爬虫

爬取环球人物网（globalpeople.com.cn）相关新闻，两层筛选涉及≥2人的新闻。

## 功能特点

- **可配置人物列表**：通过修改 `config.py` 文件，自由添加或删除想要爬取的人物
- **多关键词搜索**：每个人物支持多个搜索关键词，避免遗漏
- **两层筛选**：
  - 第一层：标题+摘要快速筛选
  - 第二层：正文内容深度筛选（仅对无法判断的新闻）
- **URL去重**：避免重复爬取相同新闻
- **日志记录**：完整记录爬取过程

## 环境要求

- Python 3.8+
- Windows / macOS / Linux

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/Bxxdx/globalpeople-scraper.git
cd globalpeople-scraper
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Playwright浏览器

```bash
playwright install chromium
```

## 配置

### 修改目标人物

编辑 `config.py` 文件，修改 `PERSONS` 字典：

```python
PERSONS = {
    "人物名称": ["人物名称", "别名1", "别名2"],
    "人物A": ["人物A", "别名A1", "别名A2"],
    "人物B": ["人物B"],
}
```

### 修改搜索URL（可选）

如果需要爬取其他网站，修改 `config.py` 中的 `SEARCH_URL`。

## 运行

```bash
python main.py
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `output/results.csv` | 筛选后的新闻数据 |
| `output/crawl.log` | 爬取日志 |

## CSV输出格式

| 字段 | 说明 |
|------|------|
| 序号 | 序号 |
| 相关人物1 | 涉及的第1个人物 |
| 相关人物2 | 涉及的第2个人物 |
| 相关人物3 | 涉及的第3个人物 |
| 标题 | 新闻标题 |
| 摘要 | 新闻摘要 |
| URL | 新闻链接 |
| 正文中与人物相关的内容 | 正文内包含人物的段落 |
| 来源 | 新闻来源 |
| 日期 | 发布日期 |
| 筛选来源 | 筛选方式（标题+摘要/正文） |

## 目录结构

```
globalpeople-scraper/
├── config.py          # 配置文件（人物名单、搜索URL）
├── crawler.py         # 爬虫核心代码
├── processor.py       # 数据处理和筛选
├── main.py            # 入口文件
├── requirements.txt   # 依赖
└── output/            # 输出目录
    ├── results.csv   # 结果文件
    └── crawl.log     # 日志文件
```

## 工作流程

```
1. 读取配置文件中的人物列表
2. 对每个人物使用多个关键词搜索
3. 遍历所有搜索结果页面
4. URL去重
5. 第一层筛选：标题+摘要快速判断
6. 第二层筛选：正文内容深度判断（仅对无法判断的新闻）
7. 输出CSV结果
```

## 常见问题

### Q: 爬取速度慢怎么办？
A: 可以减少每个人物的关键词数量，或在 `crawler.py` 中调整 `time.sleep()` 等待时间。

### Q: 被网站封禁怎么办？
A: 可以在 `config.py` 中配置代理，或增加等待时间。

### Q: 如何只爬取特定人物？
A: 编辑 `config.py` 中的 `PERSONS` 字典，只保留需要的人物。

## License

MIT
