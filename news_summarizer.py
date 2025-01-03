import requests
from bs4 import BeautifulSoup
from transformers import pipeline
import sqlite3
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
import webbrowser
import os
import re
from collections import Counter
import spacy
from wordcloud import WordCloud
from urllib.parse import urljoin
from datetime import datetime, timedelta
import pytz
import time
import feedparser
from IPython.display import HTML, display
from google.colab import files
import base64
from difflib import SequenceMatcher
from itertools import groupby
from operator import itemgetter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
import numpy as np
from io import BytesIO
import pandas as pd
import yfinance as yf

# Step 1: Web Scraping
def is_today(date_str, source):
    """检查日期是否为今天"""
    try:
        # 设置时区为美国东部时间（因为这些是美国网站）
        est = pytz.timezone('US/Eastern')
        today = datetime.now(est).date()
        
        if source == 'FierceBiotech':
            # FierceBiotech的日期格式示例: "Jan 24, 2024"
            date = datetime.strptime(date_str.strip(), '%b %d, %Y').date()
        elif source == 'BioSpace':
            # BioSpace的日期格式示例: "2024-01-24"
            date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        
        return date == today
    except Exception as e:
        print(f"日期解析错误: {str(e)}")
        return False

def is_within_last_week(date_str, source):
    """检查日期是否在最近一周内"""
    try:
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        if source == 'FierceBiotech':
            # 处理类似 "Jan 24, 2024" 的格式
            date = datetime.strptime(date_str.strip(), '%b %d, %Y')
        elif source == 'BioSpace':
            # 处理类似 "2024-01-24" 的格式
            date = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        
        return week_ago <= date <= today
    except Exception as e:
        print(f"日期解析错误: {str(e)}")
        return True  # 如果无法解析日期，默认包含该新闻

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    
    # 删除旧表（如果存在）
    c.execute("DROP TABLE IF EXISTS news")
    
    # 创建新表，包含所有必要的字段
    c.execute('''CREATE TABLE news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        link TEXT NOT NULL,
        source TEXT NOT NULL,
        content TEXT,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("数据库初始化完成")

def clean_html_title(html_title):
    """清理HTML标题"""
    soup = BeautifulSoup(html_title, 'html.parser')
    # 获取<a>标签的文本内容
    if soup.a:
        return soup.a.get_text(strip=True)
    return soup.get_text(strip=True)

def parse_date(date_str):
    """改进的日期解析函数"""
    try:
        # 处理 FierceBiotech 特殊格式 "Jan 3, 2025 9:43am"
        if isinstance(date_str, str):
            # 移除多余的空格
            date_str = ' '.join(date_str.split())
            
            # 处理带有am/pm的时间
            match = re.match(r'(\w+)\s+(\d+),\s+(\d+)\s+(\d+):(\d+)(am|pm)', date_str.lower())
            if match:
                month, day, year, hour, minute, meridiem = match.groups()
                hour = int(hour)
                if meridiem == 'pm' and hour != 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0
                
                # 构建datetime对象
                month_num = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }[month.lower()]
                
                return datetime(int(year), month_num, int(day), hour, int(minute))
        
        return datetime.now()
        
    except Exception as e:
        print(f"日期解析错误: {str(e)} for date: {date_str}")
        return datetime.now()

def scrape_rss(rss_url, source):
    """更新的RSS抓取函数"""
    print(f"开始从RSS抓取: {rss_url}")
    
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        week_ago = datetime.now() - timedelta(days=7)
        
        if source == 'BioSpace':
            rss_url = 'https://www.biospace.com/all-news.rss'
            feed = feedparser.parse(rss_url)
        
        print(f"找到 {len(feed.entries)} 条条目")
        
        for entry in feed.entries:
            try:
                # 清理标题
                clean_title = clean_html_title(entry.title)
                
                # 获取发布日期
                if hasattr(entry, 'published'):
                    pub_date = parse_date(entry.published)
                elif hasattr(entry, 'updated'):
                    pub_date = parse_date(entry.updated)
                else:
                    pub_date = datetime.now()
                
                # 检查是否在最近一周内
                if pub_date.replace(tzinfo=None) >= week_ago:
                    # 获取文章内容
                    content = ''
                    if hasattr(entry, 'content'):
                        content = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # 清理HTML标签
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        content = soup.get_text(separator=' ', strip=True)
                    
                    # 获取链接
                    link = entry.link if hasattr(entry, 'link') else ''
                    
                    news_item = {
                        'title': clean_title,
                        'link': link,
                        'source': source,
                        'date': pub_date.strftime('%Y-%m-%d'),
                        'content': content,
                        'summary': ''
                    }
                    
                    # 打印调试信息
                    print(f"\n找到文章:")
                    print(f"标题: {clean_title}")
                    print(f"日期: {news_item['date']}")
                    print(f"链接: {link}")
                    print(f"内容长度: {len(content)} 字符")
                    
                    news_list.append(news_item)
            
            except Exception as e:
                print(f"处理RSS条目时出错: {str(e)}")
                continue
        
        print(f"\n成功从{source}的RSS获取 {len(news_list)} 条最近一周的新闻")
        return news_list
    
    except Exception as e:
        print(f"RSS抓取错误: {str(e)}")
        return []

def scrape_news(base_url):
    """根据不同来源使用不同的抓取方法"""
    if 'fiercebiotech' in base_url:
        return scrape_fiercebiotech_rss()
    
    # BioSpace保持原有的抓取方法
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"\n尝试抓取: {base_url}")
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        news_list = []
        
        articles = soup.select('.article-card, .news-item')
        print(f"BioSpace: 找到 {len(articles)} 个文章元素")
        
        for article in articles:
            try:
                title_elem = (article.select_one('.article-card__title a') or 
                            article.select_one('.title a'))
                date_elem = article.select_one('.article-card__date, .date')
                
                if title_elem:
                    title = title_elem.text.strip()
                    link = urljoin(base_url, title_elem['href'])
                    date_str = date_elem.text.strip() if date_elem else datetime.now().strftime('%Y-%m-%d')
                    
                    news_list.append({
                        'title': title,
                        'link': link,
                        'source': 'BioSpace',
                        'date': date_str,
                        'content': ''
                    })
                    print(f"找到文章: {title}")
            except Exception as e:
                print(f"处理文章时出错: {str(e)}")
        
        return news_list
    
    except Exception as e:
        print(f"抓取错误: {str(e)}")
        return []

def get_article_content(url):
    """获取单个文章的详细内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content = ""
        
        # 根据网站调整选择器
        if 'fiercebiotech' in url:
            article_body = soup.select_one('.article-content')
            if article_body:
                paragraphs = article_body.select('p')
                content = ' '.join([p.text.strip() for p in paragraphs])
        
        elif 'biospace' in url:
            article_body = soup.select_one('.article__body')
            if article_body:
                paragraphs = article_body.select('p')
                content = ' '.join([p.text.strip() for p in paragraphs])
        
        return content
    except Exception as e:
        print(f"获取文章内容错误 {url}: {str(e)}")
        return ""

def store_news(news_list):
    """存储新闻，保留最近一周的新闻"""
    if not news_list:
        print("没有新闻要存储")
        return
    
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    
    # 删除一周以前的新闻
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    c.execute("DELETE FROM news WHERE date < ?", (week_ago,))
    
    for item in news_list:
        try:
            c.execute("""
                INSERT OR REPLACE INTO news (title, link, source, content, summary, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item['title'],
                item['link'],
                item['source'],
                item.get('content', ''),
                item.get('summary', ''),
                item.get('date', datetime.now().strftime('%Y-%m-%d'))
            ))
        except Exception as e:
            print(f"存储新闻时出错: {str(e)}")
    
    conn.commit()
    conn.close()
    print(f"成功存储 {len(news_list)} 条新闻")

def process_news():
    """主处理函数"""
    # 初始化数据库
    init_database()
    
    # 更新RSS源
    rss_sources = {
        'FierceBiotech': 'https://www.fiercebiotech.com/rss/xml',
        'BioSpace': 'https://www.biospace.com/all-news.rss'
    }
    
    all_news = []
    
    for source, rss_url in rss_sources.items():
        time.sleep(2)  # 添加延迟
        news_list = scrape_rss(rss_url, source)
        
        if news_list:
            for item in news_list:
                try:
                    # 如果内容太短，尝试从原文页面获取
                    if len(item.get('content', '')) < 100:
                        time.sleep(1)
                        content = get_article_content(item['link'])
                        if content:
                            item['content'] = content
                    
                    # 生成摘要
                    if item['content']:
                        summary = summarize_news([{'content': item['content']}])[0]['summary']
                        item['summary'] = summary
                    else:
                        item['summary'] = item['title']  # 如果没有内容，使用标题作为摘要
                    
                except Exception as e:
                    print(f"处理文章内容时出错: {str(e)}")
                    item['summary'] = item['title']
            
            all_news.extend(news_list)
    
    if all_news:
        store_news(all_news)
        print(f"总共处理了 {len(all_news)} 条新闻")
        return all_news
    else:
        print("没有找到任何新闻")
        return []

# Step 2: Summarization
def summarize_news(news_items, max_length=150):
    """改进的新闻摘要函数"""
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    
    for item in news_items:
        try:
            content = item.get('content', '')
            if not content:
                item['summary'] = item['title']
                continue
                
            # 限制输入长度
            content = ' '.join(content.split()[:512])  # 限制词数
            
            # 根据输入长度动态调整max_length
            input_length = len(content.split())
            max_length = min(max_length, input_length - 1)  # 确保摘要短于输入
            min_length = min(30, max_length - 1)  # 动态设置最小长度
            
            summary = summarizer(content, 
                               max_length=max_length,
                               min_length=min_length,
                               do_sample=False)[0]['summary_text']
            
            item['summary'] = summary
            
        except Exception as e:
            print(f"生成摘要时出错: {str(e)}")
            item['summary'] = item['title']  # 使用标题作为后备摘要
    
    return news_items

# Step 3: Data Visualization
def load_knowledge_base():
    """加载知识库"""
    companies = set()
    drugs = set()
    indications = set()
    
    # 加载公司名称
    try:
        with open('company_names.txt', 'r', encoding='utf-8') as f:
            companies = {line.strip() for line in f if line.strip() and not line.startswith('#')}
        print(f"从知识库加载了 {len(companies)} 个公司名称")
    except Exception as e:
        print(f"加载公司名称时出错: {str(e)}")
    
    # 加载药物名称
    try:
        with open('drug_names.txt', 'r', encoding='utf-8') as f:
            drugs = {line.strip() for line in f if line.strip() and not line.startswith('#')}
        print(f"从知识库加载了 {len(drugs)} 个药物名称")
    except Exception as e:
        print(f"加载药物名称时出错: {str(e)}")
    
    # 加载适应症
    try:
        with open('indication.txt', 'r', encoding='utf-8') as f:
            indications = {line.strip() for line in f if line.strip() and not line.startswith('#')}
        print(f"从知识库加载了 {len(indications)} 个适应症")
    except Exception as e:
        print(f"加载适应症时出错: {str(e)}")
    
    return companies, drugs, indications

def extract_entities(text):
    """改进的实体提取函数，使用知识库"""
    if not text or not isinstance(text, str):
        return [], [], []
    
    # 加载知识库
    known_companies, known_drugs, known_indications = load_knowledge_base()
    
    # 将文本转换为小写以进行匹配
    text_lower = text.lower()
    
    companies = []
    drugs = []
    indications = []
    
    # 1. 从知识库匹配公司名称
    for company in known_companies:
        if company.lower() in text_lower:
            companies.append(company)
    
    # 2. 从知识库匹配药物名称
    for drug in known_drugs:
        if drug.lower() in text_lower:
            drugs.append(drug)
    
    # 3. 从知识库匹配适应症
    for indication in known_indications:
        if indication.lower() in text_lower:
            indications.append(indication)
    
    # 4. 使用正则表达式补充识别研发代号
    drug_patterns = [
        r'\b[A-Z]{2,3}-\d{3,4}\b',  # 例如: AB-123
        r'\b[A-Z]{2,3}\d{3,4}\b',   # 例如: AB123
    ]
    
    for pattern in drug_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            drug_name = match.group()
            if drug_name not in drugs:  # 避免重复
                drugs.append(drug_name)
    
    # 5. 使用spaCy补充识别未知的公司名称
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(text)
    
    company_keywords = ['therapeutics', 'pharma', 'biotech', 'pharmaceuticals', 
                       'biosciences', 'medicines', 'medical', 'health',
                       'technologies', 'labs', 'laboratory']
    
    for ent in doc.ents:
        if ent.label_ == 'ORG':
            company_name = ent.text.strip()
            # 如果公司名称包含关键词但不在知识库中
            if (any(keyword in company_name.lower() for keyword in company_keywords) and 
                company_name not in companies):
                companies.append(company_name)
    
    # 清理和去重
    companies = list(set(companies))
    drugs = list(set(drugs))
    indications = list(set(indications))
    
    # 打印调试信息
    print(f"\n提取的实体:")
    print(f"公司: {len(companies)} 个")
    print(f"药物: {len(drugs)} 个")
    print(f"适应症: {len(indications)} 个")
    
    if companies:
        print("\n示例公司:", companies[:5])
    if drugs:
        print("\n示例药物:", drugs[:5])
    if indications:
        print("\n示例适应症:", indications[:5])
    
    return companies, drugs, indications

def create_wordcloud(words, title):
    """改进的词云生成函数，添加默认空白图片处理"""
    if not words:
        print(f"警告: {title} 没有数据")
        # 创建空白图片
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, f'No {title} data available', 
                ha='center', va='center', fontsize=14)
        plt.axis('off')
        
        # 保存空白图片
        filename = f"{title.lower().replace(' ', '_')}.png"
        plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        return filename
    
    try:
        # 统计词频
        word_freq = Counter(words)
        
        # 打印词频统计用于调试
        print(f"\n{title} 词频统计:")
        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"{word}: {freq}")
        
        # 创建词云
        wordcloud = WordCloud(
            width=800, 
            height=400,
            background_color='white',
            max_words=50,
            max_font_size=100,
            min_font_size=10,
            random_state=42,
            collocations=False
        ).generate_from_frequencies(word_freq)
        
        # 创建图形
        plt.figure(figsize=(10, 6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title(title)
        
        # 保存图片
        filename = f"{title.lower().replace(' ', '_')}.png"
        plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        return filename
        
    except Exception as e:
        print(f"生成词云时出错 ({title}): {str(e)}")
        # 创建错误提示图片
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, f'Error generating {title} word cloud', 
                ha='center', va='center', fontsize=14)
        plt.axis('off')
        
        filename = f"{title.lower().replace(' ', '_')}.png"
        plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        return filename

def create_charts():
    """改进的图表创建函数"""
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    c.execute("SELECT title, summary FROM news")
    all_texts = [f"{row[0]}. {row[1]}" for row in c.fetchall()]
    conn.close()
    
    print(f"Processing {len(all_texts)} news articles")  # 调试信息
    
    # 提取所有实体
    all_companies, all_drugs, all_indications = [], [], []
    for text in all_texts:
        companies, drugs, indications = extract_entities(text)
        all_companies.extend(companies)
        all_drugs.extend(drugs)
        all_indications.extend(indications)
    
    # 打印调试信息
    print(f"Found {len(set(all_companies))} unique companies")
    print(f"Found {len(set(all_drugs))} unique drugs")
    print(f"Found {len(set(all_indications))} unique indications")
    
    # 创建词云图
    company_cloud = create_wordcloud(all_companies, "Company Names")
    drug_cloud = create_wordcloud(all_drugs, "Drug Names")
    indication_cloud = create_wordcloud(all_indications, "Indications")
    
    return company_cloud, drug_cloud, indication_cloud

# Step 5: HTML Generation
def calculate_title_similarity(title1, title2):
    """计算两个标题的相似度"""
    # 使用SequenceMatcher计算文本相似度
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()

def group_similar_news(news_list, similarity_threshold=0.6):
    """将相似标题的新闻分组"""
    if not news_list:
        return []

    # 按标题排序，这样相似的标题会更容易被分到一组
    sorted_news = sorted(news_list, key=lambda x: x['title'])
    grouped_news = []
    processed = set()

    for i, news in enumerate(sorted_news):
        if i in processed:
            continue

        similar_group = {
            'main_title': news['title'],
            'sources': [news['source']],
            'dates': [news['date']],
            'links': [news['link']],
            'summaries': [news['summary']],
            'related_news': [news]
        }
        processed.add(i)

        # 查找相似的新闻
        for j, other_news in enumerate(sorted_news[i+1:], start=i+1):
            if j not in processed:
                similarity = calculate_title_similarity(news['title'], other_news['title'])
                if similarity >= similarity_threshold:
                    similar_group['sources'].append(other_news['source'])
                    similar_group['dates'].append(other_news['date'])
                    similar_group['links'].append(other_news['link'])
                    similar_group['summaries'].append(other_news['summary'])
                    similar_group['related_news'].append(other_news)
                    processed.add(j)

        grouped_news.append(similar_group)

    return grouped_news

def combine_similar_news(all_news, title_similarity_threshold=0.6, summary_similarity_threshold=0.4):
    """改进的新闻合并函数，更好的去重处理"""
    combined_news = []
    used_indices = set()

    for i, news in enumerate(all_news):
        if i in used_indices:
            continue

        similar_sources = []
        main_title = news['title']
        main_summary = news['summary']
        
        # 添加第一个来源
        similar_sources.append({
            'source': news['source'],
            'date': news['date'],
            'link': news['link']
        })
        used_indices.add(i)

        # 查找相似的新闻
        for j, other_news in enumerate(all_news):
            if j not in used_indices:
                title_similarity = calculate_title_similarity(main_title, other_news['title'])
                summary_similarity = calculate_title_similarity(main_summary, other_news['summary'])
                
                if title_similarity >= title_similarity_threshold or summary_similarity >= summary_similarity_threshold:
                    similar_sources.append({
                        'source': other_news['source'],
                        'date': other_news['date'],
                        'link': other_news['link']
                    })
                    used_indices.add(j)

        # 创建新闻组
        news_group = {
            'title': main_title,
            'summary': main_summary,
            'sources': similar_sources
        }
        combined_news.append(news_group)

    # 按来源数量排序
    combined_news.sort(key=lambda x: len(x['sources']), reverse=True)
    return combined_news

def generate_html():
    """改进的HTML生成函数"""
    try:
        # 更新模板，改进显示格式
        template_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>生物科技新闻摘要</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 20px;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .news-group { 
                    margin-bottom: 30px; 
                    padding: 20px;
                    border: 1px solid #eee;
                    border-radius: 5px;
                }
                .news-title {
                    font-size: 1.2em;
                    color: #333;
                    margin-bottom: 10px;
                }
                .news-summary {
                    color: #666;
                    margin-bottom: 15px;
                }
                .source-list {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                }
                .source-item {
                    background: #f5f5f5;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 0.9em;
                }
                .wordcloud-section {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }
                .wordcloud-item {
                    text-align: center;
                }
                img { 
                    max-width: 100%; 
                    height: auto;
                    border: 1px solid #eee;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>生物科技新闻摘要</h1>
            <p>时间范围: {{ date_range }}</p>
            
            <div class="wordcloud-section">
                <div class="wordcloud-item">
                    <h2>公司关键词</h2>
                    <img src="{{ company_cloud }}" alt="Company Word Cloud">
                </div>
                <div class="wordcloud-item">
                    <h2>药物关键词</h2>
                    <img src="{{ drug_cloud }}" alt="Drug Word Cloud">
                </div>
                <div class="wordcloud-item">
                    <h2>适应症关键词</h2>
                    <img src="{{ indication_cloud }}" alt="Indication Word Cloud">
                </div>
            </div>
            
            <div class="news-section">
                <h2>新闻摘要</h2>
                {% for group in combined_news %}
                <div class="news-group">
                    <div class="news-title">{{ group.title }}</div>
                    <div class="news-summary">{{ group.summary }}</div>
                    <div class="source-list">
                        {% for source in group.sources %}
                        <div class="source-item">
                            <a href="{{ source.link }}" target="_blank">{{ source.source }}</a>
                            ({{ source.date }})
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </body>
        </html>
        '''
        
        # 创建临时template文件
        with open('template.html', 'w', encoding='utf-8') as f:
            f.write(template_content)
            
        # 其余代码保持不变
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template('template.html')
        
        conn = sqlite3.connect('news.db')
        c = conn.cursor()
        
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        c.execute("""
            SELECT title, summary, link, source, date 
            FROM news 
            WHERE date >= ?
            ORDER BY date DESC
        """, (week_ago,))
        
        news = [{
            'title': row[0],
            'summary': row[1],
            'link': row[2],
            'source': row[3],
            'date': row[4]
        } for row in c.fetchall()]
        
        conn.close()
        
        combined_news = combine_similar_news(news)
        company_cloud, drug_cloud, indication_cloud = create_charts()
        
        def img_to_base64(img_path):
            with open(img_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
        
        html_content = template.render(
            combined_news=combined_news,
            company_cloud=img_to_base64(company_cloud),
            drug_cloud=img_to_base64(drug_cloud),
            indication_cloud=img_to_base64(indication_cloud),
            date_range=f"{week_ago} to {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        # 保存生成的HTML
        with open('news_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
            
    except Exception as e:
        print(f"生成HTML时出错: {str(e)}")
        raise

def generate_wordcloud(text, title):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(title)
    
    # Convert plot to base64 string
    img = BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close()
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

def cluster_similar_news(titles, summaries):
    # Combine titles and summaries for clustering
    combined_texts = [f"{t} {s}" for t, s in zip(titles, summaries)]
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(combined_texts)
    
    # Cluster using DBSCAN
    clustering = DBSCAN(eps=0.3, min_samples=2).fit(tfidf_matrix)
    
    # Group similar news
    clusters = {}
    for idx, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(idx)
    
    return clusters

def process_feeds(feeds):
    all_titles = []
    all_summaries = []
    all_links = []
    
    # Collect all news items
    for feed in feeds:
        for entry in feed.entries:
            all_titles.append(entry.title)
            all_summaries.append(entry.summary)
            all_links.append(entry.link)
    
    # Generate word clouds
    title_cloud = generate_wordcloud(' '.join(all_titles), 'Title Word Cloud')
    summary_cloud = generate_wordcloud(' '.join(all_summaries), 'Summary Word Cloud')
    
    # Create combined word cloud
    combined_text = ' '.join(all_titles + all_summaries)
    combined_cloud = generate_wordcloud(combined_text, 'Combined Word Cloud')
    
    # Cluster similar news
    clusters = cluster_similar_news(all_titles, all_summaries)
    
    # Prepare clustered news items
    clustered_news = []
    for label, indices in clusters.items():
        if label != -1:  # Skip noise points
            representative_idx = indices[0]
            similar_items = [{'title': all_titles[i], 'summary': all_summaries[i], 'link': all_links[i]} 
                           for i in indices]
            clustered_news.append({
                'main_title': all_titles[representative_idx],
                'main_summary': all_summaries[representative_idx],
                'main_link': all_links[representative_idx],
                'similar_items': similar_items[1:] if len(similar_items) > 1 else []
            })
    
    return {
        'title_cloud': title_cloud,
        'summary_cloud': summary_cloud,
        'combined_cloud': combined_cloud,
        'clustered_news': clustered_news
    }

def update_company_database():
    """从多个来源更新公司数据库"""
    companies = set()
    
    # 1. 从生物科技ETF获取公司列表
    try:
        # iShares Nasdaq Biotechnology ETF (IBB)
        ibb = yf.Ticker("IBB")
        holdings = ibb.holdings
        if holdings is not None:
            companies.update(holdings.index)
        
        # SPDR S&P Biotech ETF (XBI)
        xbi = yf.Ticker("XBI")
        holdings = xbi.holdings
        if holdings is not None:
            companies.update(holdings.index)
            
        print(f"从ETF获取了 {len(companies)} 家公司")
    except Exception as e:
        print(f"从ETF获取公司列表时出错: {str(e)}")
    
    # 2. 从FDA获取药品制造商列表
    try:
        fda_url = "https://www.fda.gov/drugs/drug-approvals-and-databases/approved-drug-products-therapeutic-equivalence-evaluations-orange-book"
        response = requests.get(fda_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 解析FDA页面获取制造商信息
            # 具体解析规则需要根据FDA网页结构调整
            manufacturers = set()  # 存储从FDA页面提取的制造商
            companies.update(manufacturers)
    except Exception as e:
        print(f"从FDA获取制造商列表时出错: {str(e)}")
    
    # 3. 保存更新后的公司列表
    try:
        # 读取现有的公司列表
        existing_companies = set()
        try:
            with open('company_names.txt', 'r', encoding='utf-8') as f:
                existing_companies = {line.strip() for line in f if line.strip() and not line.startswith('#')}
        except FileNotFoundError:
            pass
        
        # 合并新旧公司列表
        all_companies = existing_companies.union(companies)
        
        # 保存更新后的列表
        with open('company_names.txt', 'w', encoding='utf-8') as f:
            f.write("# 生物科技公司列表 - 最后更新: " + datetime.now().strftime('%Y-%m-%d') + "\n")
            for company in sorted(all_companies):
                f.write(company + "\n")
        
        print(f"更新了公司数据库，现有 {len(all_companies)} 家公司")
    except Exception as e:
        print(f"保存公司列表时出错: {str(e)}")

def update_drug_database():
    """从多个来源更新药物数据库"""
    drugs = set()
    
    # 1. 从FDA获取已批准药物列表
    try:
        # FDA Drugs@FDA 数据
        fda_url = "https://www.accessdata.fda.gov/scripts/cder/drugsatfda/index.cfm"
        response = requests.get(fda_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 查找药物名称列表
            drug_elements = soup.find_all('a', href=lambda x: x and 'appletter' in x)
            fda_drugs = {elem.text.strip() for elem in drug_elements if elem.text.strip()}
            drugs.update(fda_drugs)
            print(f"从FDA获取了 {len(fda_drugs)} 个药物")
    except Exception as e:
        print(f"从FDA获取药物列表时出错: {str(e)}")
    
    # 2. 从ClinicalTrials.gov获取药物信息
    try:
        # 使用ClinicalTrials.gov API
        ct_url = "https://clinicaltrials.gov/api/query/study_fields"
        params = {
            'expr': 'AREA[InterventionType]Drug',
            'fields': 'InterventionName',
            'min_rnk': 1,
            'max_rnk': 1000,
            'fmt': 'json'
        }
        response = requests.get(ct_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'StudyFieldsResponse' in data:
                ct_drugs = set()
                for study in data['StudyFieldsResponse'].get('StudyFields', []):
                    interventions = study.get('InterventionName', [])
                    ct_drugs.update(interventions)
                drugs.update(ct_drugs)
                print(f"从ClinicalTrials.gov获取了 {len(ct_drugs)} 个药物")
    except Exception as e:
        print(f"从ClinicalTrials.gov获取药物信息时出错: {str(e)}")
    
    # 3. 添加常见药物后缀模式的药物
    try:
        # 从现有文本中提取可能的药物名称
        drug_patterns = [
            r'\b[A-Za-z]+mab\b',  # 单克隆抗体
            r'\b[A-Za-z]+nib\b',  # 激酶抑制剂
            r'\b[A-Za-z]+zib\b',
            r'\b[A-Za-z]+mib\b',
            r'\b[A-Za-z]+tinib\b',
            r'\b[A-Za-z]+zumab\b',
            r'\b[A-Za-z]+ximab\b',
            r'\b[A-Za-z]+umab\b'
        ]
        
        # 添加一些已知的药物名称
        known_drugs = {
            # 单克隆抗体
            'Humira', 'Keytruda', 'Opdivo', 'Avastin', 'Herceptin', 'Rituxan',
            'Ocrevus', 'Darzalex', 'Dupixent', 'Stelara', 'Soliris', 'Entyvio',
            
            # 小分子药物
            'Ibrutinib', 'Lenalidomide', 'Apixaban', 'Rivaroxaban', 'Tofacitinib',
            'Baricitinib', 'Upadacitinib', 'Ruxolitinib',
            
            # 其他重要药物
            'Ozempic', 'Wegovy', 'Mounjaro', 'Jardiance', 'Eliquis', 'Xarelto',
            'Imbruvica', 'Revlimid', 'Xtandi', 'Skyrizi', 'Rinvoq', 'Vyvanse',
            
            # 生物制剂
            'Lantus', 'Trulicity', 'Eylea', 'Enbrel', 'Prevnar', 'Gardasil'
        }
        
        drugs.update(known_drugs)
        print(f"添加了 {len(known_drugs)} 个已知药物")
        
    except Exception as e:
        print(f"添加已知药物时出错: {str(e)}")
    
    # 4. 保存更新后的药物列表
    try:
        # 读取现有的药物列表
        existing_drugs = set()
        try:
            with open('drug_names.txt', 'r', encoding='utf-8') as f:
                existing_drugs = {line.strip() for line in f if line.strip() and not line.startswith('#')}
        except FileNotFoundError:
            pass
        
        # 合并新旧药物列表
        all_drugs = existing_drugs.union(drugs)
        
        # 保存更新后的列表
        with open('drug_names.txt', 'w', encoding='utf-8') as f:
            f.write("# 药物名称列表 - 最后更新: " + datetime.now().strftime('%Y-%m-%d') + "\n")
            f.write("# 包括：FDA批准药物、临床试验药物、已知重要药物\n\n")
            
            # 按类别组织药物
            categories = {
                '单克隆抗体': lambda x: x.lower().endswith(('mab', 'umab', 'zumab', 'ximab')),
                '激酶抑制剂': lambda x: x.lower().endswith(('nib', 'tinib')),
                '其他药物': lambda x: True  # 默认类别
            }
            
            for category, condition in categories.items():
                category_drugs = sorted(drug for drug in all_drugs if condition(drug))
                if category_drugs:
                    f.write(f"\n# {category}\n")
                    for drug in category_drugs:
                        f.write(drug + "\n")
        
        print(f"更新了药物数据库，现有 {len(all_drugs)} 个药物")
    except Exception as e:
        print(f"保存药物列表时出错: {str(e)}")

def update_knowledge_base():
    """更新所有知识库"""
    print("开始更新知识库...")
    
    # 更新公司数据库
    print("\n更新公司数据库...")
    update_company_database()
    
    # 更新药物数据库
    print("\n更新药物数据库...")
    update_drug_database()
    
    print("\n知识库更新完成")

def main():
    # 检查是否需要更新知识库（例如每周更新一次）
    try:
        last_update = datetime.fromtimestamp(os.path.getmtime('company_names.txt'))
        if (datetime.now() - last_update).days >= 7:
            print("知识库已超过7天未更新，开始更新...")
            update_knowledge_base()
    except FileNotFoundError:
        print("未找到知识库文件，开始创建...")
        update_knowledge_base()
    
    # 初始化数据库并处理新闻
    news = process_news()
    
    if not news:
        print("没有找到新闻数据")
        return
        
    # 生成HTML报告
    try:
        generate_html()
        
        # 在Colab中显示结果
        from IPython.display import HTML, display
        
        # 读取生成的HTML文件
        with open('news_report.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 在notebook中显示
        display(HTML(html_content))
        
        # 提供下载链接
        from google.colab import files
        files.download('news_report.html')
        
    except Exception as e:
        print(f"生成报告时出错: {str(e)}")

if __name__ == "__main__":
    # 处理新闻
    news = process_news()
    if news:  # 只在有新闻时创建图表和HTML
        create_charts()
        generate_html()
    else:
        print("由于没有新闻，跳过创建图表和HTML")