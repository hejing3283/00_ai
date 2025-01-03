class DiseaseIndications:
    """疾病适应症知识库"""
    
    INDICATIONS = {
        'cancer': {
            'name': '癌症',
            'categories': {
                'lung_cancer': {
                    'name': '肺癌',
                    'keywords': ['肺癌', '肺部肿瘤', '非小细胞肺癌', 'NSCLC'],
                    'subtypes': ['非小细胞肺癌', '小细胞肺癌'],
                    'stages': ['I期', 'II期', 'III期', 'IV期'],
                    'reliability': 0.95
                },
                'breast_cancer': {
                    'name': '乳腺癌',
                    'keywords': ['乳腺癌', '乳房肿瘤', '乳腺肿瘤'],
                    'subtypes': ['浸润性导管癌', '浸润性小叶癌'],
                    'stages': ['早期', '中期', '晚期'],
                    'reliability': 0.95
                }
            }
        },
        
        'cardiovascular': {
            'name': '心血管疾病',
            'categories': {
                'hypertension': {
                    'name': '高血压',
                    'keywords': ['高血压', '血压升高', '原发性高血压'],
                    'grades': ['1级', '2级', '3级'],
                    'reliability': 0.9
                },
                'coronary_heart_disease': {
                    'name': '冠心病',
                    'keywords': ['冠心病', '冠状动脉疾病', '心绞痛'],
                    'types': ['稳定型心绞痛', '不稳定型心绞痛'],
                    'reliability': 0.9
                }
            }
        }
    }
    
    # 这里需要从indication.txt读取并添加更多疾病类别
    
    @classmethod
    def load_from_file(cls, file_path):
        """从文件加载适应症数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            current_category = None
            current_disease = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 根据文件格式解析内容
                # 这里需要根据实际的indication.txt格式来实现解析逻辑
                
        except Exception as e:
            print(f"Error loading indications: {e}")
    
    @classmethod
    def get_all_keywords(cls):
        """获取所有疾病关键词"""
        keywords = []
        for category in cls.INDICATIONS.values():
            for disease in category['categories'].values():
                keywords.extend(disease['keywords'])
        return list(set(keywords))
    
    @classmethod
    def get_disease_by_keyword(cls, keyword):
        """根据关键词查找疾病"""
        for category in cls.INDICATIONS.values():
            for disease_id, disease in category['categories'].items():
                if keyword in disease['keywords']:
                    return disease_id, disease
        return None, None 