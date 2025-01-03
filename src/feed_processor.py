from .word_cloud_generator import WordCloudGenerator
from .news_clusterer import NewsClusterer
from .knowledge_base import MedicalKnowledgeBase

class FeedProcessor:
    def __init__(self):
        self.word_cloud_generator = WordCloudGenerator()
        self.news_clusterer = NewsClusterer()
        self.knowledge_base = MedicalKnowledgeBase()
    
    def process_feeds(self, feeds):
        all_titles = []
        all_summaries = []
        all_links = []
        all_indications = []  # 新增：存储提取的疾病指标
        
        # 收集所有新闻条目
        for feed in feeds:
            for entry in feed.entries:
                title = getattr(entry, 'title', '').strip()
                summary = getattr(entry, 'summary', '').strip()
                link = getattr(entry, 'link', '')
                
                if title and summary:
                    # 提取该条新闻中的疾病指标
                    indications = self._extract_indications(title, summary)
                    
                    if indications['has_medical_info']:  # 只保留包含医学信息的新闻
                        all_titles.append(title)
                        all_summaries.append(summary)
                        all_links.append(link)
                        all_indications.append(indications)
        
        if not all_titles:
            return self._empty_result()
        
        try:
            # 生成词云
            clouds = self._generate_clouds(all_titles, all_summaries)
            # 聚类新闻
            clustered_news = self._cluster_news(all_titles, all_summaries, all_links, all_indications)
            
            return {**clouds, 'clustered_news': clustered_news}
        
        except Exception as e:
            print(f"Error processing feeds: {e}")
            return self._empty_result()
    
    def _extract_indications(self, title, summary):
        """提取文本中的疾病指标"""
        # 合并标题和摘要进行分析
        full_text = f"{title} {summary}"
        
        # 使用知识库分析文本
        analysis_result = self.knowledge_base.analyze_text(full_text)
        
        # 整理分析结果
        result = {
            'has_medical_info': False,  # 是否包含医学信息
            'diseases': [],             # 发现的疾病
            'symptoms': [],             # 发现的症状
            'indicators': [],           # 发现的指标
            'severity': None,           # 疾病严重程度
            'confidence': 0.0           # 提取的置信度
        }
        
        # 如果发现了任何医学相关信息
        if analysis_result['diseases'] or analysis_result['symptoms'] or analysis_result['indicators']:
            result['has_medical_info'] = True
            result['diseases'] = analysis_result['diseases']
            result['symptoms'] = analysis_result['symptoms']
            result['indicators'] = analysis_result['indicators']
            
            # 计算置信度（简单平均）
            confidences = []
            for disease in analysis_result['diseases']:
                if 'reliability' in disease:
                    confidences.append(disease['reliability'])
            
            if confidences:
                result['confidence'] = sum(confidences) / len(confidences)
            
            # 评估严重程度
            result['severity'] = self._assess_severity(analysis_result)
        
        return result
    
    def _assess_severity(self, analysis_result):
        """评估疾病严重程度"""
        severity_score = 0
        severity_count = 0
        
        # 根据症状评估严重度
        for symptom in analysis_result['symptoms']:
            if symptom in self.knowledge_base.indicators.DISEASE_INDICATORS['clinical_symptoms']:
                symptom_info = self.knowledge_base.indicators.DISEASE_INDICATORS['clinical_symptoms'][symptom]
                if 'severity' in symptom_info:
                    severity_score += len(symptom_info['severity'])
                    severity_count += 1
        
        if severity_count > 0:
            avg_severity = severity_score / severity_count
            if avg_severity >= 2.5:
                return 'severe'
            elif avg_severity >= 1.5:
                return 'moderate'
            else:
                return 'mild'
        
        return 'unknown'
    
    def _cluster_news(self, titles, summaries, links, indications):
        """聚类新闻，考虑疾病指标"""
        clusters = self.news_clusterer.cluster_similar_news(titles, summaries)
        
        clustered_news = []
        for label, indices in clusters.items():
            if label != -1:  # 跳过噪声点
                representative_idx = indices[0]
                
                # 收集该簇中的所有疾病指标
                cluster_indications = {
                    'diseases': set(),
                    'symptoms': set(),
                    'indicators': set()
                }
                
                similar_items = []
                for i in indices:
                    # 添加新闻项
                    item = {
                        'title': titles[i],
                        'summary': summaries[i],
                        'link': links[i],
                        'indications': indications[i]
                    }
                    
                    # 收集疾病指标
                    for disease in indications[i]['diseases']:
                        cluster_indications['diseases'].add(disease['name'])
                    cluster_indications['symptoms'].update(indications[i]['symptoms'])
                    cluster_indications['indicators'].update(indications[i]['indicators'])
                    
                    if i != representative_idx:
                        similar_items.append(item)
                
                # 创建聚类新闻项
                clustered_news.append({
                    'main_title': titles[representative_idx],
                    'main_summary': summaries[representative_idx],
                    'main_link': links[representative_idx],
                    'main_indications': indications[representative_idx],
                    'similar_items': similar_items,
                    'cluster_indications': {
                        'diseases': list(cluster_indications['diseases']),
                        'symptoms': list(cluster_indications['symptoms']),
                        'indicators': list(cluster_indications['indicators'])
                    }
                })
        
        # 按疾病指标的置信度排序
        clustered_news.sort(key=lambda x: x['main_indications']['confidence'], reverse=True)
        
        return clustered_news
    
    def _generate_clouds(self, titles, summaries):
        """生成词云，突出显示医学术语"""
        # 获取所有医学关键词
        medical_keywords = set(
            self.knowledge_base.indications.get_all_keywords() +
            self.knowledge_base.indicators.get_symptom_keywords() +
            self.knowledge_base.indicators.get_lab_keywords()
        )
        
        # 生成词云时给医学术语更高的权重
        def weight_medical_terms(text):
            words = text.split()
            weighted_text = []
            for word in words:
                if word in medical_keywords:
                    weighted_text.extend([word] * 3)  # 医学术语权重为3
                else:
                    weighted_text.append(word)
            return ' '.join(weighted_text)
        
        return {
            'title_cloud': self.word_cloud_generator.generate_wordcloud(
                weight_medical_terms(' '.join(titles)), 'Title Word Cloud'),
            'summary_cloud': self.word_cloud_generator.generate_wordcloud(
                ' '.join(summaries), 'Summary Word Cloud'),
            'combined_cloud': self.word_cloud_generator.generate_wordcloud(
                ' '.join(titles + summaries), 'Combined Word Cloud')
        }
    
    def _empty_result(self):
        return {
            'title_cloud': '',
            'summary_cloud': '',
            'combined_cloud': '',
            'clustered_news': []
        } 