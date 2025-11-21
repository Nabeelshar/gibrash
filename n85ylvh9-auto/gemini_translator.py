"""
Gemini API translator module with glossary support
Uses REST API to avoid dependency conflicts
"""

import json
import time
import requests


class GeminiTranslator:
    def __init__(self, api_key, logger):
        self.logger = logger
        self.api_key = api_key
        self.glossary = {}
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        if not api_key:
            self.logger("WARNING: No Gemini API key provided")
            return
        
        self.logger("✓ Gemini REST API client initialized")
    
    def _call_gemini_api(self, model, prompt, temperature=0.3):
        """Call Gemini REST API"""
        url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": temperature
            }
        }
        
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        if 'candidates' in data and len(data['candidates']) > 0:
            candidate = data['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                return candidate['content']['parts'][0]['text']
        
        raise Exception("No valid response from Gemini API")
    
    def translate_description(self, description_html, raw_novel_name=None, source_lang='zh-CN', target_lang='en'):
        """
        Translate novel description with prompt to clean and extract only the description
        """
        if not self.api_key:
            self.logger("WARNING: Gemini API key not available for description translation")
            return description_html
        
        prompt = f"""You are a professional translator specializing in Chinese web novels.

Task: Translate the following Chinese novel description to English. 

Important instructions:
1. ONLY return the main story synopsis/description
2. Remove ALL markdown formatting (**, ##, bullets, etc.) - plain text only
3. Remove character profiles, tags, reading guides, author notes, upcoming novels
4. Remove "Latest Chapter:", "Update:", footers, advertisements
5. Remove translator notes, character descriptions, themes
6. Keep ONLY the core story plot description
7. Natural, engaging translation with proper paragraph breaks
8. No explanations, no comments - ONLY the synopsis text

Chinese text to translate:
{description_html}

English translation:"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                translated = self._call_gemini_api('gemini-flash-latest', prompt, temperature=0.3).strip()
                
                # Verify translation actually happened (not just returned original)
                if translated == description_html or len(translated) < 10:
                    raise Exception("Translation returned original or empty text")
                
                # Add raw novel name at the end if provided
                if raw_novel_name:
                    translated = f"{translated}\n\nRaw Novel Name: {raw_novel_name}"
                
                self.logger("  ✓ Description translated with Gemini")
                return translated
                
            except Exception as e:
                error_msg = str(e).lower()
                if attempt < max_retries - 1:
                    self.logger(f"  ⚠ Gemini description attempt {attempt + 1} failed: {e}")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger(f"  ✗ Gemini description translation failed after {max_retries} attempts: {e}")
                    # CRITICAL: Return None to signal translation failure
                    return None
    
    def generate_glossary(self, chapters_data, max_chapters=None):
        """
        Generate a glossary of names and terms from all chapters
        
        Args:
            chapters_data: List of dicts with 'title' and 'content' (Chinese)
            max_chapters: Not used (kept for compatibility)
        
        Returns:
            dict: Glossary mapping Chinese terms to English translations
        """
        if not self.api_key:
            self.logger("WARNING: Gemini API key not available for glossary generation")
            return {}
        
        self.logger(f"\n{'='*50}")
        self.logger("Generating Translation Glossary")
        self.logger(f"{'='*50}")
        self.logger(f"Analyzing all {len(chapters_data)} chapters (complete raw content)...")
        
        # Combine ALL chapters with COMPLETE content (no truncation)
        combined_text = "\n\n".join([
            f"Chapter {i+1}:\n{ch['content']}"  # Use complete chapter content
            for i, ch in enumerate(chapters_data)
        ])
        
        # Gemini has 1 million token input limit - no artificial limits needed
        self.logger(f"  Using complete content ({len(combined_text)} chars, ~{len(combined_text)//4} tokens)")
        
        prompt = f"""You are a professional translator for Chinese web novels.

Task: Analyze the following Chinese novel chapters and create a consistent English glossary for character names, place names, special terms, and cultivation/skill terms.

Instructions:
1. Extract ALL important names (characters, places, organizations) that appear in the text
2. Extract ALL cultivation terms, skill names, and special terminology
3. Provide consistent English translations that sound natural
4. For names, use pinyin or appropriate English equivalents
5. Be thorough - extract as many terms as possible for consistency
6. Return ONLY a JSON object in this exact format:

{{
  "characters": {{"中文名": "English Name", ...}},
  "places": {{"中文地名": "English Place", ...}},
  "terms": {{"中文术语": "English Term", ...}}
}}

Chinese chapters:
{combined_text}

JSON glossary:"""
        
        try:
            # Parse JSON response
            response_text = self._call_gemini_api('gemini-2.5-flash', prompt, temperature=0.2).strip()
            
            # Extract JSON from markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            glossary_data = json.loads(response_text)
            
            # Flatten glossary for easy lookup
            self.glossary = {}
            for category in ['characters', 'places', 'terms']:
                if category in glossary_data:
                    self.glossary.update(glossary_data[category])
            
            self.logger(f"✓ Glossary generated with {len(self.glossary)} entries")
            self.logger(f"  - Characters: {len(glossary_data.get('characters', {}))}")
            self.logger(f"  - Places: {len(glossary_data.get('places', {}))}")
            self.logger(f"  - Terms: {len(glossary_data.get('terms', {}))}")
            
            # Log sample entries
            if self.glossary:
                self.logger("\n  Sample glossary entries:")
                for i, (chinese, english) in enumerate(list(self.glossary.items())[:5]):
                    self.logger(f"    {chinese} → {english}")
                if len(self.glossary) > 5:
                    self.logger(f"    ... and {len(self.glossary) - 5} more")
            
            return self.glossary
            
        except json.JSONDecodeError as e:
            self.logger(f"✗ Failed to parse glossary JSON: {e}")
            self.logger(f"  Response: {response_text[:500]}")
            return {}
        except Exception as e:
            self.logger(f"✗ Glossary generation failed: {e}")
            return {}
    
    def translate_chapter_content(self, content, chapter_number, glossary=None, google_translator=None):
        """
        Translate chapter content using Gemini with glossary consistency
        Enhanced with multi-level fallback strategy
        
        Args:
            content: Chinese chapter content
            chapter_number: Chapter number for context
            glossary: Optional glossary dict (uses self.glossary if not provided)
            google_translator: Google Translate instance for fallback
        
        Returns:
            tuple: (translated_content, translation_method)
            translation_method: 'gemini', 'gemini_censored', or 'google'
        """
        if not self.api_key:
            self.logger("    WARNING: Gemini API key not available")
            return None, 'failed'
        
        if glossary is None:
            glossary = self.glossary
        
        # Build glossary instructions
        glossary_text = ""
        if glossary:
            glossary_entries = "\n".join([f"- {cn} = {en}" for cn, en in list(glossary.items())[:50]])
            glossary_text = f"""
Use this glossary for consistent translations:
{glossary_entries}
"""
        
        prompt = f"""You are a professional translator for Chinese web novels.

Task: Translate the following Chinese chapter to natural, fluent English.

Instructions:
1. Maintain narrative flow and readability
2. Use the provided glossary for consistency with previous chapters
3. Keep the same paragraph structure
4. Translate cultivation terms naturally
5. Remove ALL markdown formatting (**, ##, etc.) - plain text only
6. Do NOT include any notes, explanations, or meta-commentary
7. Output ONLY the translated chapter content

{glossary_text}

Chapter {chapter_number} content (Chinese):
{content}

English translation:"""
        
        # ATTEMPT 1: Try Gemini with original content (with retries for API errors)
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                translated = self._call_gemini_api('gemini-flash-latest', prompt, temperature=0.3).strip()
                return translated, 'gemini'
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                # Check for safety/content filtering errors - DON'T RETRY, go to fallback
                if 'SAFETY' in error_msg.upper() or 'BLOCK' in error_msg.upper() or 'HARM' in error_msg.upper():
                    self.logger(f"    ⚠ Gemini safety filter triggered: {error_msg}")
                    break  # Exit retry loop, go to fallback strategy
                
                # For other errors (API, rate limit, etc.), retry
                if attempt < max_retries - 1:
                    self.logger(f"    ⚠ Gemini attempt {attempt + 1} failed: {error_msg}")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    self.logger(f"    ✗ Gemini translation failed after {max_retries} attempts: {error_msg}")
                    return None, 'failed'
        
        # Only reach here if safety filter triggered
        if last_error:
            error_msg = str(last_error)
            if 'SAFETY' in error_msg.upper() or 'BLOCK' in error_msg.upper() or 'HARM' in error_msg.upper():
                self.logger(f"    ⚠ Gemini safety filter triggered")
                
                # ATTEMPT 2: Translate with Google Translate, then censor and retry Gemini
                if google_translator:
                    self.logger(f"    → Attempting Google Translate + censoring + Gemini retry...")
                    
                    try:
                        # Translate with Google first
                        google_translation = google_translator.translate(content)
                        
                        # Censor potentially problematic words
                        censored_translation = self._censor_content(google_translation)
                        
                        # Retry Gemini with censored English text
                        retry_prompt = f"""You are a professional editor for web novels.

Task: Improve and polish the following English text while maintaining consistency with the glossary.

Instructions:
1. Fix any awkward phrasing or grammar
2. Use the glossary for character/place names
3. Keep the same paragraph structure
4. Make the text flow naturally
5. Output ONLY the polished content

{glossary_text}

Text to polish:
{censored_translation}

Polished version:"""
                        
                        polished = self._call_gemini_api('gemini-flash-latest', retry_prompt, temperature=0.3).strip()
                        self.logger(f"    ✓ Gemini succeeded with censored content")
                        return polished, 'gemini_censored'
                        
                    except Exception as retry_error:
                        self.logger(f"    ✗ Gemini retry also failed: {retry_error}")
                        # ATTEMPT 3: Fall back to Google Translate only
                        self.logger(f"    → Using Google Translate as final fallback")
                        return google_translation, 'google'
                else:
                    return None, 'failed'
        else:
            # No error or non-safety error after retries
            return None, 'failed'
    
    def _censor_content(self, text):
        """
        Censor potentially problematic words for content filtering
        
        Args:
            text: Text to censor
            
        Returns:
            Censored text
        """
        # Common words that might trigger filters (especially for BL/gay novels)
        censor_map = {
            # Explicit content
            'dick': 'member',
            'cock': 'member',
            'penis': 'member',
            'pussy': 'flower',
            'vagina': 'flower',
            'ass': 'behind',
            'asshole': 'behind',
            'anal': 'intimate',
            'sex': 'intimacy',
            'sexy': 'attractive',
            'sexual': 'intimate',
            'fuck': 'embrace',
            'fucking': 'embracing',
            'fucked': 'embraced',
            'cum': 'finish',
            'cumming': 'finishing',
            'orgasm': 'peak',
            'aroused': 'excited',
            'erection': 'reaction',
            'hard-on': 'reaction',
            'masturbate': 'touch',
            'penetrate': 'enter',
            'penetration': 'entry',
            'thrust': 'move',
            'thrusting': 'moving',
            'moan': 'sound',
            'moaning': 'sounding',
            'groan': 'sound',
            'groaning': 'sounding',
            'lust': 'desire',
            'lustful': 'desirous',
            'seduce': 'attract',
            'seduction': 'attraction',
            'naked': 'unclothed',
            'nude': 'bare',
            'breast': 'chest',
            'nipple': 'tip',
            'kiss': 'touch',
            'kissing': 'touching',
            'lick': 'taste',
            'licking': 'tasting',
            'suck': 'draw',
            'sucking': 'drawing',
            # Violence (keep minimal since you said it's not about violence)
            'blood': 'energy',
            'bloody': 'intense',
            'corpse': 'body',
            'tortured': 'pressured',
            'pain': 'discomfort',
            'painful': 'difficult',
            'weapon': 'tool',
            'sword': 'blade',
            'knife': 'blade',
            'attack': 'strike',
            'attacked': 'struck',
            'violent': 'intense',
            'violence': 'intensity',
        }
        
        censored = text
        for original, replacement in censor_map.items():
            # Case-insensitive replacement, preserve capitalization
            import re
            pattern = re.compile(re.escape(original), re.IGNORECASE)
            
            def replace_func(match):
                orig = match.group(0)
                if orig[0].isupper():
                    return replacement.capitalize()
                return replacement
            
            censored = pattern.sub(replace_func, censored)
        
        return censored
    
    def save_glossary(self, novel_id, file_manager):
        """Save glossary to file for future reference"""
        if not self.glossary:
            return
        
        try:
            import os
            novel_dir = os.path.join('novels', f'novel_{novel_id}')
            os.makedirs(novel_dir, exist_ok=True)
            
            filepath = os.path.join(novel_dir, 'glossary.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.glossary, f, ensure_ascii=False, indent=2)
            
            self.logger(f"✓ Glossary saved to {filepath}")
        except Exception as e:
            self.logger(f"✗ Failed to save glossary: {e}")
    
    def load_glossary(self, novel_id):
        """Load existing glossary from file"""
        try:
            import os
            filepath = os.path.join('novels', f'novel_{novel_id}', 'glossary.json')
            
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.glossary = json.load(f)
                self.logger(f"✓ Loaded existing glossary with {len(self.glossary)} entries")
                return True
            return False
        except Exception as e:
            self.logger(f"✗ Failed to load glossary: {e}")
            return False
