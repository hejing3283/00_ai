from wordcloud import WordCloud
import matplotlib.pyplot as plt
import base64
from io import BytesIO

class WordCloudGenerator:
    @staticmethod
    def generate_wordcloud(text, title):
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
        
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title(title)
        
        img = BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        plt.close()
        img.seek(0)
        return base64.b64encode(img.getvalue()).decode() 