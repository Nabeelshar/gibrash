"""
Weekly Article Generator for Volarereads
Generates SEO-friendly discovery content about new novels

Following Google's guidelines:
- AI-assisted drafting with human-quality output
- Focus on helpful, unique content
- Proper schema markup
- No generic spam content
"""

import os
import sys
import json
import random
import requests
from datetime import datetime, timedelta
from config_loader import load_config

# Article templates - rotates weekly to avoid repetition
ARTICLE_TEMPLATES = [
    {
        "type": "weekly_roundup",
        "title_template": "This Week's Fresh BL Picks: {date_range}",
        "focus": "New arrivals and why they're worth reading"
    },
    {
        "type": "trope_spotlight", 
        "title_template": "Hidden Gems: {trope} Novels You Might Have Missed",
        "focus": "Specific trope exploration with novel recommendations"
    },
    {
        "type": "mood_based",
        "title_template": "What to Read When You Want {mood}",
        "focus": "Novels categorized by reading mood/experience"
    },
    {
        "type": "character_types",
        "title_template": "For Fans of {character_type}: Your Next Obsession Awaits",
        "focus": "Character archetype recommendations"
    }
]

# Tropes for rotation
BL_TROPES = [
    "Cold Gong x Sunny Shou",
    "Enemies to Lovers", 
    "Second Chance Romance",
    "Rebirth/Transmigration",
    "Office Romance",
    "Historical/Ancient Setting",
    "Modern Day Slice of Life",
    "Fantasy Adventure",
    "Omegaverse",
    "Slow Burn Romance"
]

# Moods for rotation
READING_MOODS = [
    "Something Sweet and Fluffy",
    "An Emotional Rollercoaster",
    "A Slow Burn That Pays Off",
    "Action with Romance on the Side",
    "Something Light and Funny"
]

# Character types
CHARACTER_TYPES = [
    "the Tsundere Gong",
    "the Scheming Shou", 
    "the Gentle Giant",
    "the Misunderstood Villain",
    "the Loyal Second Lead"
]


class WeeklyArticleGenerator:
    def __init__(self):
        self.config = load_config()
        self.wordpress_url = self.config.get('wordpress_url', '').rstrip('/')
        self.api_key = self.config.get('api_key', '')
        self.gemini_api_key = self.config.get('gemini_api_key', '')
        
    def get_recent_novels(self, days=7):
        """Fetch novels added in the last N days from WordPress"""
        try:
            # Use custom crawler API endpoint
            url = f"{self.wordpress_url}/wp-json/crawler/v1/stories/recent"
            params = {
                'days': days,
                'per_page': 20,
            }
            headers = {'X-API-Key': self.api_key}
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('stories', [])
            else:
                print(f"Failed to fetch novels: {response.status_code}")
                print(response.text)
                return []
                
        except Exception as e:
            print(f"Error fetching novels: {e}")
            return []
    
    def get_novel_details(self, novel_id):
        """Get detailed info about a novel including chapter count"""
        try:
            url = f"{self.wordpress_url}/wp-json/wp/v2/fcn_story/{novel_id}"
            headers = {'X-API-Key': self.api_key}
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    def select_article_template(self):
        """Select article template based on week number for variety"""
        week_num = datetime.now().isocalendar()[1]
        template_idx = week_num % len(ARTICLE_TEMPLATES)
        return ARTICLE_TEMPLATES[template_idx]
    
    def generate_article_with_gemini(self, novels, template):
        """Use Gemini to generate a human-quality article"""
        if not self.gemini_api_key:
            print("No Gemini API key - cannot generate article")
            return None
            
        # Prepare novel data for the prompt
        novel_summaries = []
        for novel in novels[:5]:  # Max 5 novels per article
            title = novel.get('title', {}).get('rendered', 'Unknown')
            excerpt = novel.get('excerpt', {}).get('rendered', '')
            link = novel.get('link', '')
            
            # Clean HTML from excerpt
            import re
            excerpt_clean = re.sub(r'<[^>]+>', '', excerpt)[:300]
            
            novel_summaries.append({
                'title': title,
                'excerpt': excerpt_clean,
                'link': link
            })
        
        # Select trope/mood/character based on week
        week_num = datetime.now().isocalendar()[1]
        trope = BL_TROPES[week_num % len(BL_TROPES)]
        mood = READING_MOODS[week_num % len(READING_MOODS)]
        char_type = CHARACTER_TYPES[week_num % len(CHARACTER_TYPES)]
        
        # Build the prompt based on template type
        date_range = f"{(datetime.now() - timedelta(days=7)).strftime('%b %d')} - {datetime.now().strftime('%b %d, %Y')}"
        
        if template['type'] == 'weekly_roundup':
            title = template['title_template'].format(date_range=date_range)
            focus = "a weekly roundup of new BL novels"
        elif template['type'] == 'trope_spotlight':
            title = template['title_template'].format(trope=trope)
            focus = f"novels featuring the '{trope}' trope"
        elif template['type'] == 'mood_based':
            title = template['title_template'].format(mood=mood)
            focus = f"novels perfect for readers wanting {mood.lower()}"
        else:
            title = template['title_template'].format(character_type=char_type)
            focus = f"novels featuring {char_type}"
        
        novels_text = "\n".join([
            f"- {n['title']}: {n['excerpt']}" for n in novel_summaries
        ])
        
        prompt = f"""You are a passionate BL (Boys' Love) novel enthusiast writing for Volarereads.com. 
Write an engaging blog article about {focus}.

CRITICAL RULES:
1. Write like an excited fan sharing recommendations with friends, NOT like a corporate blog
2. Use casual, warm language with personality
3. Include specific details that show you've actually read these novels
4. Add personal opinions and reactions (e.g., "I literally couldn't put this down")
5. NO generic phrases like "immerse yourself" or "captivating journey"
6. NO AI-sounding language - write like a real person
7. Include 1-2 mild spoiler-free teasers to hook readers
8. End with a question to encourage comments

ARTICLE TITLE: {title}

NOVELS TO FEATURE (pick 3-4 that fit the theme best):
{novels_text}

FORMAT:
- Opening hook (2-3 sentences, personal and engaging)
- Brief intro to the theme/trope (1 paragraph)
- Each novel recommendation (2-3 paragraphs each with WHY it's good)
- Personal favorite pick with reasoning
- Closing question for readers

LENGTH: 600-900 words
TONE: Enthusiastic fan, slightly informal, genuine

Write the article now:"""

        try:
            # Call Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.8,  # Higher for more creative/human output
                    "maxOutputTokens": 2000
                }
            }
            
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']
                return {
                    'title': title,
                    'content': content,
                    'novels_featured': [n['title'] for n in novel_summaries[:4]]
                }
            else:
                print(f"Gemini API error: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Error generating article: {e}")
            return None
    
    def create_schema_markup(self, article_data, novels):
        """Generate proper schema.org markup for SEO"""
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article_data['title'],
            "author": {
                "@type": "Organization",
                "name": "Volarereads",
                "url": "https://volarereads.com"
            },
            "publisher": {
                "@type": "Organization", 
                "name": "Volarereads",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://volarereads.com/wp-content/uploads/logo.png"
                }
            },
            "datePublished": datetime.now().isoformat(),
            "dateModified": datetime.now().isoformat(),
            "mainEntityOfPage": {
                "@type": "WebPage"
            },
            "about": [
                {
                    "@type": "Book",
                    "name": novel,
                    "genre": "Boys' Love"
                } for novel in article_data.get('novels_featured', [])
            ]
        }
        return json.dumps(schema, indent=2)
    
    def post_to_wordpress(self, article_data, schema_markup):
        """Post the article to WordPress as a blog post"""
        try:
            # Add schema to content
            content_with_schema = f"""
<script type="application/ld+json">
{schema_markup}
</script>

{article_data['content']}

<hr>
<p><em>Looking for more recommendations? Check out our <a href="https://volarereads.com/stories/">full novel library</a> or join our <a href="#">Discord community</a> to chat with fellow readers!</em></p>
"""
            
            # Use custom crawler API endpoint
            url = f"{self.wordpress_url}/wp-json/crawler/v1/article"
            headers = {
                'X-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            post_data = {
                'title': article_data['title'],
                'content': content_with_schema,
                'status': 'publish',
                'meta_description': f"Discover this week's best BL novel recommendations on Volarereads. {article_data['title']}"
            }
            
            response = requests.post(url, json=post_data, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"✓ Article published: {result.get('link')}")
                return result
            else:
                print(f"Failed to publish: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Error posting to WordPress: {e}")
            return None
    
    def run(self):
        """Main execution"""
        print("\n" + "="*60)
        print("Weekly Article Generator - Volarereads")
        print("="*60)
        
        # 1. Get recent novels
        print("\n[1/4] Fetching recent novels...")
        novels = self.get_recent_novels(days=7)
        
        if not novels:
            print("No novels found from the past week. Skipping article generation.")
            return False
        
        print(f"  Found {len(novels)} novels from the past week")
        
        # 2. Select article template
        print("\n[2/4] Selecting article template...")
        template = self.select_article_template()
        print(f"  Template: {template['type']}")
        print(f"  Focus: {template['focus']}")
        
        # 3. Generate article with Gemini
        print("\n[3/4] Generating article with Gemini...")
        article_data = self.generate_article_with_gemini(novels, template)
        
        if not article_data:
            print("Failed to generate article")
            return False
        
        print(f"  Title: {article_data['title']}")
        print(f"  Featuring: {', '.join(article_data['novels_featured'])}")
        
        # 4. Create schema and post
        print("\n[4/4] Publishing to WordPress...")
        schema = self.create_schema_markup(article_data, novels)
        result = self.post_to_wordpress(article_data, schema)
        
        if result:
            print("\n" + "="*60)
            print("✓ Weekly article published successfully!")
            print("="*60)
            return True
        
        return False


def main():
    generator = WeeklyArticleGenerator()
    success = generator.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
