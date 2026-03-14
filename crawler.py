import time
import logging
from typing import List, Dict, Set
from playwright.sync_api import Page, sync_playwright
from bs4 import BeautifulSoup
import config


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/crawl.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_browser():
    """创建浏览器实例"""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    return playwright, browser


def close_browser(playwright, browser):
    """关闭浏览器"""
    browser.close()
    playwright.stop()


def build_search_url(keyword: str) -> str:
    """构建搜索URL"""
    return f"{config.SEARCH_URL}?keywords={keyword}"


def get_total_count(page: Page) -> int:
    """获取搜索结果总数"""
    try:
        total_elem = page.locator('#totalCount')
        if total_elem.count() > 0:
            text = total_elem.first.inner_text()
            return int(text)
    except:
        pass
    return 0


def get_current_page_items_count(page: Page) -> int:
    """获取当前页新闻数量"""
    try:
        items = page.locator('.items')
        return items.count()
    except:
        return 0


def parse_page(html: str) -> List[Dict]:
    """解析搜索结果页"""
    soup = BeautifulSoup(html, 'lxml')
    items = soup.select('.items')
    
    results = []
    for item in items:
        try:
            link_elem = item.select_one('a')
            title_elem = item.select_one('.title')
            text_elem = item.select_one('.text')
            origin_elem = item.select_one('.origin_name')
            date_elem = item.select_one('.show-date')
            
            url = link_elem.get('href', '') if link_elem else ''
            title = title_elem.get_text(strip=True) if title_elem else ''
            summary = text_elem.get_text(strip=True) if text_elem else ''
            origin = origin_elem.get_text(strip=True) if origin_elem else ''
            date = date_elem.get_text(strip=True) if date_elem else ''
            
            if url and title:
                results.append({
                    'url': url,
                    'title': title,
                    'summary': summary,
                    'origin': origin,
                    'date': date
                })
        except Exception as e:
            logger.warning(f"解析单条新闻失败: {e}")
            continue
    
    return results


def has_next_page(page: Page) -> bool:
    """检查是否有下一页"""
    try:
        next_btn = page.locator('.next')
        if next_btn.count() > 0:
            is_disabled = next_btn.first.get_attribute('disabled')
            if is_disabled:
                return False
            style = next_btn.first.get_attribute('style')
            if style and 'display' in style and 'none' in style:
                return False
            return True
        return False
    except:
        return False


def crawl_keyword(page: Page, person: str, keyword: str) -> List[Dict]:
    """爬取单个关键词的新闻"""
    results = []
    search_url = build_search_url(keyword)
    
    try:
        page.goto(search_url, timeout=30000)
        page.wait_for_selector('.items', timeout=15000)
        time.sleep(2)
        
        total_count = get_total_count(page)
        items_per_page = get_current_page_items_count(page)
        
        if items_per_page > 0:
            total_pages = (total_count + items_per_page - 1) // items_per_page
        else:
            total_pages = 1
        
        if total_count > 0:
            logger.info(f"  [{person}] 关键词[{keyword}]: 共{total_count}条, 预计{total_pages}页")
        
        page_count = 0
        while True:
            page_count += 1
            
            html = page.content()
            page_results = parse_page(html)
            
            for r in page_results:
                r['search_person'] = person
                r['search_keyword'] = keyword
            results.extend(page_results)
            
            if page_count >= total_pages:
                break
            
            if has_next_page(page):
                page.click('.next')
                page.wait_for_load_state('networkidle', timeout=15000)
                time.sleep(1)
            else:
                break
                
    except Exception as e:
        logger.error(f"爬取关键词[{keyword}]时出错: {e}")
    
    return results


def crawl_person(page: Page, person: str, keywords: List[str]) -> List[Dict]:
    """爬取单个人物的所有关键词新闻"""
    all_results = []
    
    logger.info(f"开始爬取人物: {person}")
    
    for keyword in keywords:
        results = crawl_keyword(page, person, keyword)
        all_results.extend(results)
        time.sleep(0.5)
    
    logger.info(f"完成人物[{person}], 共获取 {len(all_results)} 条新闻")
    return all_results


def crawl_all_persons() -> List[Dict]:
    """爬取所有人物的新闻"""
    playwright, browser = create_browser()
    context = browser.new_context()
    page = context.new_page()
    
    all_news = []
    url_set: Set[str] = set()
    
    logger.info("=" * 60)
    logger.info("开始爬取所有人物的新闻")
    logger.info("=" * 60)
    
    for person, keywords in config.PERSONS.items():
        results = crawl_person(page, person, keywords)
        
        # URL去重
        deduplicated = []
        for r in results:
            if r['url'] not in url_set:
                url_set.add(r['url'])
                deduplicated.append(r)
        
        all_news.extend(deduplicated)
        logger.info(f"  → 去重后累计: {len(all_news)} 条")
    
    close_browser(playwright, browser)
    
    logger.info("=" * 60)
    logger.info(f"总计获取 {len(all_news)} 条新闻 (去重后)")
    logger.info("=" * 60)
    return all_news


def fetch_article_body(page: Page, url: str) -> str:
    """获取文章正文内容"""
    try:
        page.goto(url, timeout=30000)
        page.wait_for_selector('.show_content', timeout=15000)
        time.sleep(1)
        
        html = page.content()
        soup = BeautifulSoup(html, 'lxml')
        
        content_div = soup.select_one('.show_content')
        if content_div:
            return content_div.get_text(strip=True)
        
        return ""
    except Exception as e:
        logger.warning(f"获取文章正文失败: {url}, 错误: {e}")
        return ""
