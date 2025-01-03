import feedparser
from src.feed_processor import FeedProcessor
from src.html_generator import HtmlGenerator

def get_feeds():
    # 你的 RSS feed URLs
    feed_urls = [
        'http://example.com/feed1.xml',
        'http://example.com/feed2.xml'
    ]
    
    return [feedparser.parse(url) for url in feed_urls]

def main():
    # 获取 feeds
    feeds = get_feeds()
    
    # 处理 feeds
    processor = FeedProcessor()
    processed_data = processor.process_feeds(feeds)
    
    # 生成 HTML
    generator = HtmlGenerator()
    generator.generate_html(processed_data)

if __name__ == "__main__":
    main() 