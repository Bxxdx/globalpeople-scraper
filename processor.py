import pandas as pd
import config
import logging
import crawler
import re


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/crawl.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def build_keyword_map():
    """构建关键词到人物的映射"""
    keyword_to_person = {}
    for person, keywords in config.PERSONS.items():
        for kw in keywords:
            keyword_to_person[kw] = person
    return keyword_to_person


KEYWORD_TO_PERSON = build_keyword_map()


def match_persons(text: str) -> list:
    """在文本中匹配人物，返回人物列表（去重）"""
    text = text or ''
    found_persons = set()
    
    # 按关键词长度排序，优先匹配长的
    sorted_keywords = sorted(KEYWORD_TO_PERSON.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword in text:
            found_persons.add(KEYWORD_TO_PERSON[keyword])
    
    return list(found_persons)


def match_persons_with_keywords(text: str) -> tuple:
    """在文本中匹配人物，返回(人物列表, 匹配的关键词)"""
    text = text or ''
    found_persons = set()
    matched_keywords = set()
    
    sorted_keywords = sorted(KEYWORD_TO_PERSON.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword in text:
            found_persons.add(KEYWORD_TO_PERSON[keyword])
            matched_keywords.add(keyword)
    
    return list(found_persons), list(matched_keywords)


def filter_by_title_summary(news_list: list) -> tuple:
    """第一层筛选：标题+摘要"""
    logger.info("第一层筛选：标题+摘要")
    
    quick_pass = []   # ≥2人，直接通过
    need_body = []    # <2人，需要查正文
    
    for news in news_list:
        title = news.get('title', '')
        summary = news.get('summary', '')
        
        combined_text = title + ' ' + summary
        matched_persons, matched_kw = match_persons_with_keywords(combined_text)
        
        news['matched_persons'] = matched_persons
        news['matched_keywords'] = matched_kw
        news['person_count'] = len(matched_persons)
        
        if len(matched_persons) >= 2:
            news['source'] = '标题+摘要'
            quick_pass.append(news)
        else:
            need_body.append(news)
    
    logger.info(f"  标题+摘要直接通过(≥2人): {len(quick_pass)} 条")
    logger.info(f"  需要查正文(<2人): {len(need_body)} 条")
    
    return quick_pass, need_body


def extract_related_paragraphs(body: str, persons: list) -> dict:
    """从正文中提取包含人物的段落"""
    if not body:
        return {'paragraphs': [], 'persons': [], 'content': ''}
    
    # 按段落分割
    paragraphs = body.split('\n')
    
    related_paragraphs = []
    found_persons = set()
    
    for para in paragraphs:
        para = para.strip()
        if len(para) < 10:  # 跳过太短的段落
            continue
        
        # 检查段落中是否包含人物
        para_persons, _ = match_persons_with_keywords(para)
        if para_persons:
            related_paragraphs.append(para)
            found_persons.update(para_persons)
    
    # 取前3个相关段落
    content = '\n'.join(related_paragraphs[:3])
    
    return {
        'paragraphs': related_paragraphs[:3],
        'persons': list(found_persons),
        'content': content
    }


def filter_by_body(need_body_news: list, page) -> list:
    """第二层筛选：正文内容"""
    logger.info("第二层筛选：正文内容")
    
    deep_pass = []
    
    for i, news in enumerate(need_body_news):
        logger.info(f"  正在处理正文 {i+1}/{len(need_body_news)}: {news.get('title', '')[:30]}...")
        
        url = news.get('url', '')
        
        # 获取正文
        body = crawler.fetch_article_body(page, url)
        
        if not body:
            logger.warning(f"    未能获取正文: {url}")
            continue
        
        # 提取相关段落
        result = extract_related_paragraphs(body, config.PERSONS.keys())
        
        news['body_related_content'] = result['content']
        news['body_persons'] = result['persons']
        
        # 合并标题+摘要的人物和正文的人物
        title_persons = set(news.get('matched_persons', []))
        body_persons = set(result['persons'])
        all_persons = list(title_persons | body_persons)
        
        news['matched_persons'] = all_persons
        news['person_count'] = len(all_persons)
        
        if len(all_persons) >= 2:
            news['source'] = '正文'
            deep_pass.append(news)
            logger.info(f"    ✓ 找到相关人物: {all_persons}")
        else:
            logger.info(f"    ✗ 人物不足: {all_persons}")
    
    logger.info(f"  正文筛选通过(≥2人): {len(deep_pass)} 条")
    return deep_pass


def filter_all_news(news_list: list) -> list:
    """两层筛选：标题+摘要 + 正文"""
    # 第一层
    quick_pass, need_body = filter_by_title_summary(news_list)
    
    # 如果没有需要查正文的，直接返回
    if not need_body:
        return quick_pass
    
    # 第二层：需要启动浏览器获取正文
    from playwright.sync_api import sync_playwright
    
    playwright, browser = crawler.create_browser()
    context = browser.new_context()
    page = context.new_page()
    
    try:
        deep_pass = filter_by_body(need_body, page)
    finally:
        crawler.close_browser(playwright, browser)
    
    # 合并结果
    all_results = quick_pass + deep_pass
    
    logger.info(f"最终筛选结果: {len(all_results)} 条")
    return all_results


def format_output(news_list: list) -> list:
    """格式化输出数据"""
    output = []
    
    for i, news in enumerate(news_list, 1):
        persons = news.get('matched_persons', [])
        
        # 补齐3个人物位置
        person1 = persons[0] if len(persons) > 0 else ''
        person2 = persons[1] if len(persons) > 1 else ''
        person3 = persons[2] if len(persons) > 2 else ''
        
        # 获取正文相关内容
        body_content = news.get('body_related_content', '')
        if not body_content:
            body_content = ''
        
        output.append({
            '序号': i,
            '相关人物1': person1,
            '相关人物2': person2,
            '相关人物3': person3,
            '标题': news.get('title', ''),
            '摘要': news.get('summary', ''),
            'URL': news.get('url', ''),
            '正文中与人物相关的内容': body_content,
            '来源': news.get('origin', ''),
            '日期': news.get('date', ''),
            '筛选来源': news.get('source', '')
        })
    
    return output


def save_to_csv(news_list: list, output_path: str = 'output/results.csv'):
    """保存结果到CSV"""
    if not news_list:
        logger.warning("没有符合条件的新闻")
        return
    
    output_data = format_output(news_list)
    
    df = pd.DataFrame(output_data)
    
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    logger.info(f"结果已保存到: {output_path}")
    logger.info(f"共 {len(df)} 条新闻")


def print_stats(news_list: list):
    """打印统计信息"""
    logger.info("=" * 50)
    logger.info("统计信息")
    logger.info("=" * 50)
    logger.info(f"筛选后新闻总数: {len(news_list)}")
    
    # 统计人物组合
    person_combos = {}
    for news in news_list:
        persons = tuple(sorted(news.get('matched_persons', [])))
        person_combos[persons] = person_combos.get(persons, 0) + 1
    
    logger.info("\n人物组合统计 (前10):")
    for combo, count in sorted(person_combos.items(), key=lambda x: -x[1])[:10]:
        logger.info(f"  {' + '.join(combo)}: {count}条")
    
    # 统计各人物出现次数
    person_count = {}
    for news in news_list:
        for person in news.get('matched_persons', []):
            person_count[person] = person_count.get(person, 0) + 1
    
    logger.info("\n各人物出现次数:")
    for person, count in sorted(person_count.items(), key=lambda x: -x[1]):
        logger.info(f"  {person}: {count}条")
    
    logger.info("=" * 50)
