#!/usr/bin/env python3
"""
Novel Crawler for xbanxia.cc
Crawls novels and posts them to WordPress via REST API
Enhanced with Gemini AI for content translation
"""

import sys
import os
import json
import time
from translator import Translator
from gemini_translator import GeminiTranslator
from parser import NovelParser
from wordpress_api import WordPressAPI
from file_manager import FileManager
from config_loader import load_config


class NovelCrawler:
    def __init__(self, config_path='config.json'):
        """Initialize the crawler with configuration"""
        self.config = load_config(config_path)
        
        # Configuration
        self.wordpress_url = self.config['wordpress_url']
        self.api_key = self.config['api_key']
        self.google_project_id = self.config.get('google_project_id', '')
        self.google_credentials_file = self.config.get('google_credentials_file', '')
        self.gemini_api_key = self.config.get('gemini_api_key', '')
        self.max_chapters = self.config.get('max_chapters_per_run', 5)
        self.delay = self.config.get('delay_between_requests', 2)
        self.should_translate = self.config.get('translate', False)
        self.target_language = self.config.get('target_language', 'en')
        self.use_gemini_for_content = self.config.get('use_gemini_for_content', True)
        
        # Initialize Google Translate (for titles and fallback)
        self.translator = None
        if self.should_translate:
            import os
            if self.google_credentials_file:
                cred_file = os.path.join(os.path.dirname(__file__), self.google_credentials_file)
            else:
                cred_file = None
            self.translator = Translator(self.google_project_id, self.log, cred_file)
        
        # CRITICAL: Verify translator initialized
        if self.should_translate:
            if not self.translator or not self.translator.client:
                self.log("CRITICAL ERROR: Translation Required But Unavailable")
                self.log("Google Translate (googletrans) is required for this crawler")
                self.log("It's used for title translation and as fallback when Gemini censors content")
                self.log("")
                self.log("The package is in requirements.txt but may not have initialized properly")
                self.log("This could be a compatibility issue with Python 3.13")
                self.log("")
                self.log("Please check requirements.txt includes: googletrans==4.0.0rc1")
                raise Exception("Translation service initialization failed")
        
        # Initialize Gemini translator (for descriptions and chapter content)
        self.gemini_translator = None
        if self.use_gemini_for_content and self.gemini_api_key:
            self.gemini_translator = GeminiTranslator(self.gemini_api_key, self.log)
            if not self.gemini_translator.api_key:
                self.log("WARNING: Gemini API not available, will use Google Translate for all content")
                self.use_gemini_for_content = False
        
        self.parser = NovelParser(self.log)
        self.wordpress = WordPressAPI(self.wordpress_url, self.api_key, self.log)
        self.file_manager = FileManager(self.log)
        
        # Cache connection test result to reduce WordPress API calls
        self.wordpress_connection_tested = False
    
    def log(self, message):
        """Print log message with Unicode error handling"""
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('ascii', 'replace').decode('ascii'))
    
    def crawl_category(self, category_url, max_pages=None):
        """Crawl all novels from a category page with pagination"""
        self.log("\n" + "="*50)
        self.log("Starting Category Crawler")
        self.log("="*50 + "\n")
        self.log(f"Category URL: {category_url}\n")
        
        current_url = category_url
        page_count = 0
        total_novels_processed = 0
        
        while current_url:
            page_count += 1
            
            # Stop if max_pages limit reached
            if max_pages and page_count > max_pages:
                self.log(f"\n✓ Reached max pages limit ({max_pages})")
                break
            
            try:
                # Parse category page
                self.log(f"\n{'='*50}")
                self.log(f"Processing Page {page_count}")
                self.log(f"{'='*50}")
                self.log(f"URL: {current_url}\n")
                
                novels, pagination = self.parser.parse_category_page(current_url)
                
                self.log(f"Found {len(novels)} novels on page {pagination['current']}/{pagination['total']}")
                
                # Process each novel on this page
                for idx, novel_url in enumerate(novels, 1):
                    self.log(f"\n--- Novel {idx}/{len(novels)} on Page {page_count} ---")
                    self.log(f"URL: {novel_url}")
                    
                    try:
                        self.crawl_novel(novel_url)
                        total_novels_processed += 1
                    except KeyboardInterrupt:
                        self.log("\n\n⚠ Interrupted by user")
                        self.log(f"Processed {total_novels_processed} novels across {page_count} pages")
                        return
                    except Exception as e:
                        self.log(f"✗ Error crawling novel: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # Move to next page
                current_url = pagination.get('next')
                
                if current_url:
                    self.log(f"\n→ Moving to next page: {current_url}")
                    time.sleep(self.delay)  # Delay between pages
                else:
                    self.log(f"\n✓ Reached last page ({pagination['current']}/{pagination['total']})")
                    break
                    
            except KeyboardInterrupt:
                self.log("\n\n⚠ Interrupted by user")
                self.log(f"Processed {total_novels_processed} novels across {page_count} pages")
                return
            except Exception as e:
                self.log(f"\n✗ Error processing page: {e}")
                import traceback
                traceback.print_exc()
                break
        
        self.log("\n" + "="*50)
        self.log("Category Crawling Complete!")
        self.log("="*50)
        self.log(f"Total pages processed: {page_count}")
        self.log(f"Total novels processed: {total_novels_processed}")
        self.log("")
    
    def crawl_novel(self, novel_url):
        """Main crawling process"""
        self.log("\n" + "="*50)
        self.log("Starting Novel Crawler")
        self.log("="*50 + "\n")
        
        # Check crawler state for this novel
        crawler_state = self.file_manager.load_crawler_state()
        novel_progress = crawler_state['processed_novels'].get(novel_url, {})
        
        resume_from_chapter = 0
        
        # Check if novel is truly completed (all chapters processed)
        if novel_progress.get('status') == 'completed':
            chapters_crawled = novel_progress.get('chapters_crawled', 0)
            chapters_total = novel_progress.get('chapters_total', 0)
            
            # Only skip if all chapters are truly done
            if chapters_crawled >= chapters_total:
                self.log(f"✓ Novel already fully completed: {novel_url}")
                self.log(f"  All {chapters_crawled}/{chapters_total} chapters processed")
                self.log(f"  Story ID: {novel_progress.get('story_id')}")
                return
            else:
                # Marked completed but not all chapters done - resume
                self.log(f"⟳ Novel marked completed but has more chapters: {novel_url}")
                self.log(f"  Resuming from chapter {chapters_crawled + 1}")
                resume_from_chapter = chapters_crawled
        
        if novel_progress.get('status') == 'in_progress':
            resume_from_chapter = novel_progress.get('chapters_crawled', 0)
            self.log(f"⟳ Resuming novel: {novel_url}")
            self.log(f"  Continuing from chapter {resume_from_chapter + 1}")
            self.log(f"  Progress: {resume_from_chapter}/{novel_progress.get('chapters_total')} chapters")
        
        # Step 1: Test WordPress connection (cached after first success)
        if not self.wordpress_connection_tested:
            self.log("[1/6] Testing WordPress API connection...")
            success, result = self.wordpress.test_connection()
            if success:
                self.log(f"  Connected (WordPress v{result.get('wordpress', 'unknown')})")
                self.wordpress_connection_tested = True
            else:
                self.log(f"  Failed: {result}")
                return
        else:
            self.log("[1/6] WordPress connection (cached ✓)")
        
        # Step 2: Fetch and parse novel page
        self.log("\n[2/6] Fetching novel page...")
        novel_data, novel_id = self.parser.parse_novel_page(novel_url)
        self.log(f"  Fetched ({len(str(novel_data))} bytes)")
        
        # Step 3: Parse novel data
        self.log("\n[3/6] Parsing novel data...")
        self.log(f"  Title: {novel_data['title']}")
        self.log(f"  Author: {novel_data['author']}")
        self.log(f"  Chapters found: {len(novel_data['chapters'])}")
        
        # Step 4: Translate title and description
        self.log("\n[4/6] Translating metadata...")
        if self.should_translate and self.translator and self.translator.client:
            # Check if already translated in metadata
            existing_metadata_path = os.path.join('novels', f'novel_{novel_id}', 'metadata.json')
            if os.path.exists(existing_metadata_path):
                try:
                    with open(existing_metadata_path, 'r', encoding='utf-8') as f:
                        existing_meta = json.load(f)
                        if existing_meta.get('title_translated'):
                            translated_title = existing_meta['title_translated']
                            self.log(f"  Using cached title: {translated_title}")
                        else:
                            # Use Google Translate for title
                            translated_title = self.translator.translate(novel_data['title'])
                            # Capitalize first letter of each word
                            translated_title = translated_title.title()
                            self.log(f"  Title (EN - Google Translate): {translated_title}")
                        
                        if existing_meta.get('description_translated'):
                            translated_description = existing_meta['description_translated']
                            self.log(f"  Using cached description")
                        else:
                            # CRITICAL: Description MUST be translated
                            if self.use_gemini_for_content and self.gemini_translator:
                                translated_description = self.gemini_translator.translate_description(novel_data['description'], raw_novel_name=novel_data['title'])
                                if translated_description is None:
                                    self.log(f"  ✗ CRITICAL: Description translation failed completely")
                                    self.log(f"  Aborting - cannot publish untranslated content")
                                    return
                                self.log(f"  Description (EN - Gemini): Translated & cleaned")
                            else:
                                translated_description = self.translator.translate(novel_data['description'])
                                self.log(f"  Description (EN - Google Translate): Translated")
                except:
                    # Use Google Translate for title
                    translated_title = self.translator.translate(novel_data['title'])
                    # Capitalize first letter of each word
                    translated_title = translated_title.title()
                    self.log(f"  Title (EN - Google Translate): {translated_title}")
                    
                    # CRITICAL: Description MUST be translated
                    if self.use_gemini_for_content and self.gemini_translator:
                        translated_description = self.gemini_translator.translate_description(novel_data['description'], raw_novel_name=novel_data['title'])
                        if translated_description is None:
                            self.log(f"  ✗ CRITICAL: Description translation failed completely")
                            self.log(f"  Aborting - cannot publish untranslated content")
                            return
                        self.log(f"  Description (EN - Gemini): Translated & cleaned")
                    else:
                        translated_description = self.translator.translate(novel_data['description'])
                        self.log(f"  Description (EN - Google Translate): Translated")
            else:
                # Use Google Translate for title
                translated_title = self.translator.translate(novel_data['title'])
                # Capitalize first letter of each word
                translated_title = translated_title.title()
                self.log(f"  Title (EN - Google Translate): {translated_title}")
                
                # CRITICAL: Description MUST be translated
                if self.use_gemini_for_content and self.gemini_translator:
                    translated_description = self.gemini_translator.translate_description(novel_data['description'], raw_novel_name=novel_data['title'])
                    if translated_description is None:
                        self.log(f"  ✗ CRITICAL: Description translation failed completely")
                        self.log(f"  Aborting - cannot publish untranslated content")
                        return
                    self.log(f"  Description (EN - Gemini): Translated & cleaned")
                else:
                    translated_description = self.translator.translate(novel_data['description'])
                    self.log(f"  Description (EN - Google Translate): Translated")
        else:
            translated_title = novel_data['title']
            translated_description = novel_data['description']
            self.log("  Translation disabled")
        
        # Step 5: Check if story exists in WordPress using translated title
        self.log("\n[5/6] Checking if story exists...")
        story_data_check = {
            'title': translated_title,  # Use translated title for lookup
            'description': translated_description,  # Use translated description
            'title_zh': novel_data['title'],
            'author': novel_data['author'],
            'url': novel_url,
            'cover_url': novel_data['cover_url'],
            'cover_path': None  # Don't download yet
        }
        
        story_result = self.wordpress.create_story(story_data_check)
        story_id = story_result['id']
        
        if story_result.get('existed'):
            self.log(f"  Story exists (ID: {story_id})")
        else:
            patreon_status = " [Patreon: Volare ALL Novels]" if story_result.get('patreon_gating') else ""
            self.log(f"  Story created (ID: {story_id}){patreon_status}")
        
        if story_result.get('existed'):
            # 🚀 OPTIMIZATION: Check if all chapters exist BEFORE downloading cover
            chapter_status = self.wordpress.get_story_chapter_status(story_id, len(novel_data['chapters']))
            
            if chapter_status['success'] and chapter_status['is_complete']:
                self.log(f"  ✓✓✓ NOVEL COMPLETE! All {chapter_status['chapters_count']} chapters exist - SKIPPING! ✓✓✓")
                # Update progress and exit early
                self.file_manager.update_novel_progress(novel_url, 'completed', 
                    chapters_crawled=len(novel_data['chapters']),
                    chapters_total=len(novel_data['chapters']),
                    story_id=story_id)
                return
            else:
                self.log(f"  Novel incomplete ({chapter_status['chapters_count']}/{len(novel_data['chapters'])} chapters) - continuing...")
        
        # Only download cover if we're processing chapters
        self.log("\n[5/6] Downloading cover...")
        # Download cover image if available
        cover_path = None
        if novel_data['cover_url']:
            try:
                cover_filename = self.file_manager.download_cover(novel_id, novel_data['cover_url'])
                cover_path = os.path.join('novels', f'novel_{novel_id}', cover_filename)
                self.log(f"  Cover downloaded: {cover_filename}")
            except Exception as e:
                self.log(f"  Failed to download cover: {e}")
        
        # Save metadata
        metadata = {
            'title': novel_data['title'],
            'title_translated': translated_title,
            'author': novel_data['author'],
            'description': novel_data['description'],
            'description_translated': translated_description,
            'type': novel_data['type'],
            'status': novel_data['status'],
            'cover_url': novel_data['cover_url'],
            'source_url': novel_url,
            'total_chapters': len(novel_data['chapters'])
        }
        self.file_manager.save_metadata(novel_id, metadata)
        
        # Always update WordPress story with complete metadata after translation/download
        # This ensures cover, description, and translated title are all up-to-date
        story_data_final = {
            'title': translated_title,
            'description': translated_description,
            'title_zh': novel_data['title'],
            'author': novel_data['author'],
            'url': novel_url,
            'cover_url': novel_data['cover_url'],
            'cover_path': cover_path
        }
        self.wordpress.create_story(story_data_final)
        
        # Step 6: Process chapters with TWO-PASS SYSTEM
        self.log(f"\n[6/6] Processing chapters (max {self.max_chapters})...")
        
        # Create chapter directories
        self.file_manager.create_directories(novel_id)
        
        chapters_created = 0
        chapters_existed = 0
        
        # Store novel titles for chapter filenames
        novel_title_raw = novel_data['title']
        novel_title_translated = translated_title
        
        # Determine chapter range to process
        start_chapter = resume_from_chapter + 1
        end_chapter = min(resume_from_chapter + self.max_chapters, len(novel_data['chapters']))
        chapters_to_process = novel_data['chapters'][resume_from_chapter:end_chapter]
        
        if resume_from_chapter > 0:
            self.log(f"  Resuming from chapter {start_chapter} to {end_chapter}")
        
        # Get existing chapters (already checked in step 5, but get details for processing)
        # CPU OPTIMIZATION: Cache this result to avoid repeated API calls
        if not hasattr(self, '_cached_chapter_status') or self._cached_chapter_status.get('story_id') != story_id:
            chapter_status = self.wordpress.get_story_chapter_status(story_id, len(novel_data['chapters']))
            self._cached_chapter_status = {'story_id': story_id, 'status': chapter_status}
        else:
            chapter_status = self._cached_chapter_status['status']
            self.log(f"  Using cached chapter status (CPU optimization)")
        
        if chapter_status['success']:
            if chapter_status['chapters_count'] > 0:
                self.log(f"  Found {chapter_status['chapters_count']} existing chapters - will skip those")
                existing_chapter_set = set(chapter_status['existing_chapters'])
            else:
                existing_chapter_set = set()
        else:
            # Fallback: will check individually
            self.log("  Bulk check unavailable - checking chapters individually")
            existing_chapter_set = None
        
        # ========== PASS 1: Download all chapters ==========
        self.log(f"\n  {'='*50}")
        self.log(f"  PASS 1: Downloading raw chapters")
        self.log(f"  {'='*50}")
        
        chapters_raw_data = []
        for idx, chapter in enumerate(chapters_to_process, start=start_chapter):
            # Check if chapter exists (use bulk result if available)
            if existing_chapter_set is not None:
                if idx in existing_chapter_set:
                    self.log(f"    Chapter {idx}: Already in WordPress - Skipped")
                    chapters_existed += 1
                    continue
            else:
                # Fallback to individual check
                chapter_check = self.wordpress.check_chapter_exists(story_id, idx)
                if chapter_check['exists']:
                    self.log(f"    Chapter {idx}: Already in WordPress - Skipped")
                    chapters_existed += 1
                    continue
            
            self.log(f"    Chapter {idx}: Downloading...")
            
            # Parse chapter content
            title, content = self.parser.parse_chapter_page(chapter['url'])
            if not content:
                self.log(f"      Skipped (no content found)")
                continue
            
            self.log(f"      Extracted {len(content)} characters")
            
            # Store for glossary generation and translation
            chapters_raw_data.append({
                'idx': idx,
                'title': title,
                'content': content,
                'url': chapter['url']
            })
            
            # Delay between requests
            if idx < end_chapter:
                time.sleep(self.delay)
        
        # CPU OPTIMIZATION: Batch save all raw chapters at once (reduces file I/O)
        if chapters_raw_data:
            self.log(f"\n  Saving {len(chapters_raw_data)} raw chapters...")
            for ch_data in chapters_raw_data:
                raw_filename = self.file_manager.save_chapter(novel_id, ch_data['idx'], ch_data['title'], ch_data['content'], novel_title_raw, is_translated=False)
            self.log(f"  ✓ All raw chapters saved")
        
        # ========== PASS 2: Generate glossary and translate ==========
        if self.should_translate and len(chapters_raw_data) > 0:
            self.log(f"\n  {'='*50}")
            self.log(f"  PASS 2: Generating glossary and translating")
            self.log(f"  {'='*50}")
            
            # Try to load existing glossary or generate new one
            glossary_loaded = False
            if self.use_gemini_for_content and self.gemini_translator:
                glossary_loaded = self.gemini_translator.load_glossary(novel_id)
                
                if not glossary_loaded:
                    # Generate glossary from all downloaded chapters
                    self.log(f"\n  Generating glossary from all {len(chapters_raw_data)} chapters...")
                    self.gemini_translator.generate_glossary(chapters_raw_data)
                    self.gemini_translator.save_glossary(novel_id, self.file_manager)
            
            # Prepare list for bulk chapter upload
            chapters_to_upload = []
            
            # Translate each chapter
            for ch_data in chapters_raw_data:
                idx = ch_data['idx']
                title = ch_data['title']
                content = ch_data['content']
                
                self.log(f"\n    Chapter {idx}: Translating...")
                
                # Check if translated file already exists
                translated_dir = os.path.join('novels', f'novel_{novel_id}', 'chapters_translated')
                safe_novel_name = novel_title_translated.replace(' ', '_').replace('/', '_').replace('\\', '_')[:50]
                translated_filepath = os.path.join(translated_dir, f"{safe_novel_name}_Chapter_{idx:03d}.html")
                
                if os.path.exists(translated_filepath):
                    # Read existing translation
                    with open(translated_filepath, 'r', encoding='utf-8') as f:
                        translated_html = f.read()
                        # Extract title and content from HTML
                        import re
                        title_match = re.search(r'<h1>(.*?)</h1>', translated_html, re.DOTALL)
                        translated_title = title_match.group(1) if title_match else f"Chapter {idx}"
                        content_match = re.search(r'</h1>\s*(.+)', translated_html, re.DOTALL)
                        translated_content = content_match.group(1).strip() if content_match else content
                    self.log(f"      Using cached translation")
                else:
                    # Use simple chapter number as title (no translation needed)
                    translated_title = f"Chapter {idx}"
                    self.log(f"      Title: {translated_title}")
                    
                    # Translate content with Gemini (with enhanced fallback strategy)
                    if self.use_gemini_for_content and self.gemini_translator:
                        self.log(f"      Attempting Gemini translation...")
                        gemini_result, translation_method = self.gemini_translator.translate_chapter_content(
                            content, idx, self.gemini_translator.glossary, self.translator
                        )
                        
                        if translation_method == 'gemini':
                            translated_content = gemini_result
                            self.log(f"      ✓ Content translated with Gemini ({len(translated_content)} chars)")
                        elif translation_method == 'gemini_censored':
                            translated_content = gemini_result
                            self.log(f"      ✓ Content translated with Gemini (via censored retry) ({len(translated_content)} chars)")
                        elif translation_method == 'google':
                            translated_content = gemini_result
                            self.log(f"      ✓ Content translated with Google Translate (Gemini censored retry failed)")
                        else:
                            # Complete fallback to Google Translate
                            self.log(f"      ⚠ All Gemini attempts failed, using Google Translate...")
                            max_retries = 10
                            retry_delay = 0
                            
                            for attempt in range(max_retries):
                                try:
                                    if attempt > 0:
                                        self.log(f"      Retry {attempt}/{max_retries} (waiting {retry_delay}s)...")
                                        time.sleep(retry_delay)
                                    
                                    translated_content = self.translator.translate(content)
                                    self.log(f"      ✓ Content translated with Google Translate")
                                    break
                                except Exception as e:
                                    self.log(f"      Translation error: {e}")
                                    if attempt < max_retries - 1:
                                        retry_delay = min(600, 2 ** attempt)
                                    else:
                                        self.log(f"      CRITICAL: Translation failed after {max_retries} attempts")
                                        self.log(f"      STOPPING: Cannot proceed without translation")
                                        return
                                try:
                                    if attempt > 0:
                                        self.log(f"      Retry {attempt}/{max_retries} (waiting {retry_delay}s)...")
                                        time.sleep(retry_delay)
                                    
                                    translated_content = self.translator.translate(content)
                                    self.log(f"      ✓ Content translated with Google Translate")
                                    break
                                except Exception as e:
                                    self.log(f"      Translation error: {e}")
                                    if attempt < max_retries - 1:
                                        retry_delay = min(600, 2 ** attempt)
                                    else:
                                        self.log(f"      CRITICAL: Translation failed after {max_retries} attempts")
                                        self.log(f"      STOPPING: Cannot proceed without translation")
                                        return
                    else:
                        # Use Google Translate only
                        max_retries = 10
                        retry_delay = 0
                        
                        for attempt in range(max_retries):
                            try:
                                if attempt > 0:
                                    self.log(f"      Retry {attempt}/{max_retries} (waiting {retry_delay}s)...")
                                    time.sleep(retry_delay)
                                
                                translated_content = self.translator.translate(content)
                                self.log(f"      ✓ Content translated with Google Translate")
                                break
                            except Exception as e:
                                self.log(f"      Translation error: {e}")
                                if attempt < max_retries - 1:
                                    retry_delay = min(600, 2 ** attempt)
                                else:
                                    self.log(f"      CRITICAL: Translation failed after {max_retries} attempts")
                                    return
                
                # Store chapter data for bulk upload (save to disk later in batch)
                chapter_wordpress_title = f"{novel_title_translated} Chapter {idx}"
                chapters_to_upload.append({
                    'title': chapter_wordpress_title,
                    'title_zh': title,
                    'content': translated_content,
                    'story_id': story_id,
                    'url': ch_data['url'],
                    'chapter_number': idx
                })
            
            # CPU OPTIMIZATION: Batch save all translated chapters at once
            self.log(f"\n  Saving {len(chapters_to_upload)} translated chapters...")
            for i, ch_upload in enumerate(chapters_to_upload):
                ch_data = chapters_raw_data[i]
                translated_filename = self.file_manager.save_chapter(
                    novel_id, ch_upload['chapter_number'], 
                    ch_upload['title'], ch_upload['content'], 
                    novel_title_translated, is_translated=True
                )
            self.log(f"  ✓ All translated chapters saved")
        
        # ========== PASS 3: Bulk upload to WordPress ==========
        if self.should_translate and len(chapters_to_upload) > 0:
            self.log(f"\n  {'='*50}")
            self.log(f"  PASS 3: Uploading {len(chapters_to_upload)} chapters to WordPress")
            self.log(f"  {'='*50}")
            
            # Try bulk upload first (much faster - single API call) with retries
            bulk_success = False
            max_bulk_retries = 3
            
            for bulk_attempt in range(max_bulk_retries):
                try:
                    if bulk_attempt > 0:
                        retry_delay = 2 ** bulk_attempt  # 2s, 4s, 8s
                        self.log(f"\n  Bulk upload retry {bulk_attempt}/{max_bulk_retries} (waiting {retry_delay}s)...")
                        time.sleep(retry_delay)
                    else:
                        self.log(f"\n  Attempting bulk upload (1 API call)...")
                    
                    results = self.wordpress.create_chapters_bulk(chapters_to_upload)
                    
                    # Process results in order
                    last_idx = 0
                    for i, result in enumerate(results):
                        idx = chapters_to_upload[i]['chapter_number']
                        last_idx = idx
                        if result.get('existed'):
                            self.log(f"    Chapter {idx}: Already existed (ID: {result['id']})")
                            chapters_existed += 1
                        else:
                            scheduled_info = f" (scheduled for {result.get('publish_date', 'N/A')})" if result.get('scheduled') else " (published)"
                            self.log(f"    Chapter {idx}: ✓ Created (ID: {result['id']}){scheduled_info}")
                            chapters_created += 1
                    
                    # CPU OPTIMIZATION: Update progress once after bulk upload (not per chapter)
                    self.file_manager.update_novel_progress(
                        novel_url, 'in_progress',
                        chapters_crawled=last_idx,
                        chapters_total=len(novel_data['chapters']),
                        story_id=story_id
                    )
                    
                    self.log(f"  ✓ Bulk upload complete!")
                    bulk_success = True
                    break
                    
                except Exception as bulk_error:
                    if bulk_attempt < max_bulk_retries - 1:
                        self.log(f"  ✗ Bulk upload attempt {bulk_attempt + 1} failed: {bulk_error}")
                    else:
                        # Final attempt failed, fallback to individual
                        self.log(f"  ✗ All bulk upload attempts failed: {bulk_error}")
            
            # Fallback to individual uploads if bulk failed
            if not bulk_success:
                self.log(f"  → Falling back to individual uploads with scheduling...")
                
                for chapter_idx, chapter_data in enumerate(chapters_to_upload):
                    idx = chapter_data['chapter_number']
                    self.log(f"\n    Chapter {idx}: Uploading individually...")
                    
                    # Add chapter_index for scheduling (0 for first, 1 for second, etc.)
                    chapter_data['chapter_index'] = chapter_idx
                    
                    # Retry with exponential backoff
                    max_retries = 10
                    retry_delay = 0
                    chapter_created = False
                    
                    for attempt in range(max_retries):
                        try:
                            if attempt > 0:
                                self.log(f"      Retry {attempt}/{max_retries} (waiting {retry_delay}s)...")
                                time.sleep(retry_delay)
                            
                            chapter_result = self.wordpress.create_chapter(chapter_data)
                            if chapter_result.get('existed'):
                                self.log(f"      Already exists (ID: {chapter_result['id']})")
                                chapters_existed += 1
                            else:
                                scheduled_info = f" (scheduled)" if chapter_result.get('scheduled') else " (published)"
                                self.log(f"      ✓ Created (ID: {chapter_result['id']}){scheduled_info}")
                                chapters_created += 1
                            chapter_created = True
                            break
                        except Exception as e:
                            self.log(f"      Error: {e}")
                            if attempt < max_retries - 1:
                                retry_delay = min(600, 2 ** attempt)
                            else:
                                self.log(f"      CRITICAL: Failed after {max_retries} attempts")
                                self.log(f"      STOPPING: Cannot proceed without chapter {idx}")
                                return
                    
                    if not chapter_created:
                        self.log(f"      CRITICAL: Failed to create chapter {idx}")
                        self.log(f"      STOPPING: Chapter sequence is critical")
                        self.file_manager.update_novel_progress(
                            novel_url, 'failed',
                            chapters_crawled=idx-1,
                            chapters_total=len(novel_data['chapters']),
                            story_id=story_id
                        )
                        return
                    
                    # Update progress
                    self.file_manager.update_novel_progress(
                        novel_url, 'in_progress',
                        chapters_crawled=idx,
                        chapters_total=len(novel_data['chapters']),
                        story_id=story_id
                    )
        else:
            # No translation needed - just upload existing chapters
            for ch_data in chapters_raw_data:
                idx = ch_data['idx']
                
                chapter_wordpress_title = f"{novel_title_raw} Chapter {idx}"
                chapter_data = {
                    'title': chapter_wordpress_title,
                    'title_zh': ch_data['title'],
                    'content': ch_data['content'],
                    'story_id': story_id,
                    'url': ch_data['url'],
                    'chapter_number': idx
                }
                
                self.wordpress.create_chapter(chapter_data)
                chapters_created += 1
        
        # Determine if novel is completed or just reached max_chapters limit
        total_chapters_crawled = chapters_created + chapters_existed
        if total_chapters_crawled >= len(novel_data['chapters']):
            # All chapters processed - mark as completed
            status = 'completed'
            self.log("\n✓ All chapters processed!")
        else:
            # More chapters available - mark as in_progress
            status = 'in_progress'
            self.log(f"\n⚠ Reached max_chapters limit ({self.max_chapters}). {len(novel_data['chapters']) - total_chapters_crawled} chapters remaining.")
        
        self.file_manager.update_novel_progress(
            novel_url, status,
            chapters_crawled=total_chapters_crawled,
            chapters_total=len(novel_data['chapters']),
            story_id=story_id
        )
        
        # Summary
        self.log("\n" + "="*50)
        self.log("Crawling Complete!")
        self.log("="*50)
        self.log(f"Story ID: {story_id}")
        self.log(f"Chapters created: {chapters_created}")
        self.log(f"Chapters existed: {chapters_existed}")
        self.log(f"Total processed: {chapters_created + chapters_existed}")
        self.log("")


def main():
    if len(sys.argv) < 2:
        print("Usage: python crawler.py <url> [max_pages]")
        print("\nExamples:")
        print("  Novel:    python crawler.py https://www.xbanxia.cc/books/396941.html")
        print("  Category: python crawler.py https://www.xbanxia.cc/list/1_1.html")
        print("  Category: python crawler.py https://www.xbanxia.cc/list/1_1.html 5")
        sys.exit(1)
    
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        crawler = NovelCrawler()
        
        # Detect URL type and call appropriate method
        if '/list/' in url:
            # Category URL
            crawler.crawl_category(url, max_pages)
        elif '/books/' in url:
            # Novel URL
            crawler.crawl_novel(url)
        else:
            print(f"Error: Unknown URL type: {url}")
            print("URL should contain either '/list/' (category) or '/books/' (novel)")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
