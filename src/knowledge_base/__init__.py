from .indicators import IndicatorKnowledge
from .disease_indications import DiseaseIndications

class MedicalKnowledgeBase:
    """医学知识库"""
    
    def __init__(self):
        self.indicators = IndicatorKnowledge()
        self.indications = DiseaseIndications()
        
        # 如果有indication.txt文件，加载它
        try:
            self.indications.load_from_file('data/indication.txt')
        except Exception as e:
            print(f"Warning: Could not load indications file: {e}")
    
    def analyze_text(self, text):
        """分析文本中的医学信息"""
        results = {
            'diseases': [],
            'symptoms': [],
            'indicators': []
        }
        
        # 检查疾病关键词
        for keyword in self.indications.get_all_keywords():
            if keyword in text:
                disease_id, disease = self.indications.get_disease_by_keyword(keyword)
                if disease:
                    results['diseases'].append({
                        'id': disease_id,
                        'name': disease['name'],
                        'keyword_matched': keyword
                    })
        
        # 检查症状关键词
        for symptom in self.indicators.get_symptom_keywords():
            if symptom in text:
                results['symptoms'].append(symptom)
        
        # 检查指标关键词
        for indicator in self.indicators.get_lab_keywords():
            if indicator in text:
                results['indicators'].append(indicator)
        
        return results 