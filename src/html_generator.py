from jinja2 import Environment, FileSystemLoader
import os

class HtmlGenerator:
    def __init__(self, template_dir='templates'):
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def generate_html(self, data, output_file='output.html'):
        template = self.env.get_template('template.html')
        html_content = template.render(
            title_cloud=data['title_cloud'],
            summary_cloud=data['summary_cloud'],
            combined_cloud=data['combined_cloud'],
            clustered_news=data['clustered_news']
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content) 