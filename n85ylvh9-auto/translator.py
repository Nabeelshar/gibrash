"""
Translation module using googletrans-py (free Google Translate API)
This is used for titles and as fallback for content translation
"""

try:
    from googletrans import Translator as GoogletransTranslator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False


class Translator:
    def __init__(self, project_id, logger, credentials_file=None):
        self.logger = logger
        self.client = None
        self.service = None
        
        if GOOGLETRANS_AVAILABLE:
            try:
                self.client = GoogletransTranslator()
                self.service = 'googletrans'
                self.logger("Using googletrans-py (free Google Translate API) for titles")
                return
            except Exception as e:
                self.logger(f"ERROR: Could not initialize googletrans: {type(e).__name__}: {e}")
                import traceback
                self.logger(f"Traceback: {traceback.format_exc()}")
        
        # No translator available
        self.client = None
    
    def translate(self, text, source_lang='zh-CN', target_lang='en'):
        """Translate text using googletrans (for titles and fallback)"""
        if not self.client:
            self.logger("Warning: No translator available")
            return text
        
        try:
            return self._translate_googletrans(text, source_lang, target_lang)
        except Exception as e:
            self.logger(f"Translation error: {e}")
            return text
    
    def _translate_googletrans(self, text, source, target):
        """Translate using googletrans with chunking for long texts"""
        max_length = 4500  # Under 5000 limit
        
        # Map language codes
        source = source.replace('zh-CN', 'zh-cn')
        
        if len(text) <= max_length:
            result = self.client.translate(text, src=source, dest=target)
            return result.text
        else:
            # Split by paragraphs and group into chunks
            paragraphs = text.split('\n\n')
            translated_paragraphs = []
            current_chunk = []
            current_length = 0
            
            for para in paragraphs:
                if current_length + len(para) > max_length and current_chunk:
                    # Translate current chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    result = self.client.translate(chunk_text, src=source, dest=target)
                    translated_paragraphs.append(result.text)
                    
                    # Start new chunk
                    current_chunk = [para]
                    current_length = len(para)
                else:
                    current_chunk.append(para)
                    current_length += len(para)
            
            # Translate remaining chunk
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                result = self.client.translate(chunk_text, src=source, dest=target)
                translated_paragraphs.append(result.text)
            
            return '\n\n'.join(translated_paragraphs)
