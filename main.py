import logging
import crawler
import processor


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/crawl.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("环球人物网新闻爬虫启动")
    logger.info("目标: 爬取17人相关新闻，两层筛选涉及≥2人的新闻")
    logger.info("=" * 60)
    
    logger.info("[步骤1/3] 开始爬取新闻...")
    all_news = crawler.crawl_all_persons()
    
    logger.info("[步骤2/3] 两层筛选（标题+摘要 → 正文）...")
    filtered_news = processor.filter_all_news(all_news)
    
    logger.info("[步骤3/3] 保存结果...")
    processor.save_to_csv(filtered_news, 'output/results.csv')
    
    processor.print_stats(filtered_news)
    
    logger.info("爬虫执行完成!")


if __name__ == "__main__":
    main()
