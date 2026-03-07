"""
Web Scraper - Extract data from websites intelligently
"""
import logging
import requests
from typing import Optional, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebScraper:
    """Intelligent web scraping"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
    
    def scrape_url(self, url: str) -> Dict:
        """Scrape content from URL"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Extract metadata
            title = soup.find('title')
            title_text = title.string if title else "No title"
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc['content'] if meta_desc and 'content' in meta_desc.attrs else ""
            
            # Extract links
            links = [a.get('href') for a in soup.find_all('a', href=True)][:20]
            
            return {
                'success': True,
                'url': url,
                'title': title_text,
                'description': description,
                'text': text[:5000],  # First 5000 chars
                'links': links,
                'status_code': response.status_code
            }
        
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def extract_article(self, url: str) -> Optional[str]:
        """Extract main article content"""
        result = self.scrape_url(url)
        if not result['success']:
            return None
        
        return f"Title: {result['title']}\n\n{result['text']}"
    
    def search_google(self, query: str) -> str:
        """Search Google and return results"""
        try:
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            for g in soup.find_all('div', class_='g')[:5]:
                title_elem = g.find('h3')
                link_elem = g.find('a')
                
                if title_elem and link_elem:
                    title = title_elem.get_text()
                    link = link_elem.get('href')
                    results.append(f"• {title}\n  {link}")
            
            return "\n\n".join(results) if results else "No results found"
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"❌ Search error: {str(e)}"
