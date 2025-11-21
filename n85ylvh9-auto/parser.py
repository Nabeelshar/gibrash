"""
HTML parser module for xbanxia.cc novels
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class NovelParser:
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def parse_novel_page(self, url):
        """Parse novel page to extract metadata and chapter list"""
        response = self.session.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract novel ID from URL
        novel_id = url.rstrip('/').split('/')[-1].replace('.html', '')
        
        # Extract metadata
        novel_data = {
            'title': '',
            'author': '',
            'description': '',
            'cover_url': '',
            'type': '',
            'status': '',
            'last_updated': '',
            'latest_chapter': '',
            'chapters': []
        }
        
        # Find book intro section
        book_intro = soup.find('div', class_='book-intro')
        if book_intro:
            # Title
            h1 = book_intro.find('h1')
            if h1:
                novel_data['title'] = h1.get_text(strip=True)
            
            # Cover image
            img = book_intro.find('img', class_='lazy')
            if img:
                novel_data['cover_url'] = img.get('data-original', img.get('src', ''))
            
            # Extract metadata from paragraphs
            book_describe = book_intro.find('div', class_='book-describe')
            if book_describe:
                paragraphs = book_describe.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text.startswith('作者'):
                        author_link = p.find('a')
                        if author_link:
                            novel_data['author'] = author_link.get_text(strip=True)
                    elif text.startswith('類型'):
                        novel_data['type'] = text.replace('類型︰', '').strip()
                    elif text.startswith('狀態'):
                        novel_data['status'] = text.replace('狀態︰', '').strip()
                    elif text.startswith('最近更新'):
                        novel_data['last_updated'] = text.replace('最近更新︰', '').strip()
                    elif text.startswith('最新章節'):
                        latest_link = p.find('a')
                        if latest_link:
                            novel_data['latest_chapter'] = latest_link.get_text(strip=True)
                
                # Description - preserve HTML formatting
                describe_html = book_describe.find('div', class_='describe-html')
                if describe_html:
                    # Get HTML content with preserved tags
                    desc_html = str(describe_html)
                    # Clean up extra whitespace but keep <br> and <p> tags
                    import re
                    desc_html = re.sub(r'>\s+<', '><', desc_html)
                    novel_data['description'] = desc_html
        
        # Extract chapters from book-list section
        book_list = soup.find('div', class_='book-list')
        if book_list:
            chapter_links = book_list.find_all('a')
            for link in chapter_links:
                chapter_url = urljoin(url, link.get('href', ''))
                chapter_title = link.get('title', link.get_text(strip=True))
                
                # Only include if it's a valid chapter URL
                if '/books/' in chapter_url and chapter_url != url:
                    novel_data['chapters'].append({
                        'title': chapter_title,
                        'url': chapter_url
                    })
        
        return novel_data, novel_id
    
    def parse_category_page(self, url):
        """Parse category page to extract novel URLs"""
        response = self.session.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'lxml')
        
        novels = []
        
        # Find all novel links in pop-books2 section
        pop_books = soup.find('div', class_='pop-books2')
        if pop_books:
            novel_items = pop_books.find_all('li', class_='pop-book2')
            for item in novel_items:
                link = item.find('a', href=True)
                if link and '/books/' in link['href']:
                    novels.append(urljoin(url, link['href']))
        
        # Extract pagination info from pagelink div
        pagination = {'current': 1, 'total': 1, 'next': None}
        pagelink = soup.find('div', class_='pagelink')
        if pagelink:
            # Get current and total pages from pagestats
            pagestats = pagelink.find('em', id='pagestats')
            if pagestats:
                stats_text = pagestats.get_text()
                if '/' in stats_text:
                    current, total = stats_text.split('/')
                    pagination['current'] = int(current)
                    pagination['total'] = int(total)
            
            # Get next page URL from next link
            next_link = pagelink.find('a', class_='next')
            if next_link:
                pagination['next'] = urljoin(url, next_link['href'])
        
        return novels, pagination
    
    def parse_chapter_page(self, url):
        """Parse chapter page to extract content"""
        response = self.session.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract chapter title
        title_elem = soup.find('h1', id='nr_title')
        title = title_elem.get_text(strip=True) if title_elem else ''
        
        # Extract chapter content from div#nr1
        content_elem = soup.find('div', id='nr1')
        if not content_elem:
            return None, None
        
        # Remove script tags and other unwanted elements
        for tag in content_elem.find_all(['script', 'style']):
            tag.decompose()
        
        # Get the text content
        content = content_elem.get_text(separator='\n', strip=True)
        
        # Clean up the content
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        # Remove common footer text
        lines = [line for line in lines if '本站無彈出廣告' not in line]
        content = '\n\n'.join(lines)
        
        return title, content
