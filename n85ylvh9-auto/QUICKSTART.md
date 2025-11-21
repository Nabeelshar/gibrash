# Quick Start Guide - Gemini Translation

## 🚀 Setup Steps

### 1. Install Dependencies

```bash
cd "c:\Users\Nab\Local Sites\volarenewnovels\app\public\wp-content\plugins\ai novels\crawler\crawler"
pip install -r requirements.txt
```

### 2. Get Gemini API Key

1. Visit: https://aistudio.google.com/app/apikey
2. Click "Get API Key" or "Create API Key"
3. Copy your API key

### 3. Configure API Key

Edit `config.json` and add your Gemini API key:

```json
{
  "wordpress_url": "http://volarenewnovels.local",
  "api_key": "Fr9yOke8qhGvVthc65gp0CQVvacrW0Cb",
  "gemini_api_key": "PUT_YOUR_GEMINI_API_KEY_HERE",
  "max_chapters_per_run": 999,
  "delay_between_requests": 2,
  "translate": true,
  "target_language": "en",
  "use_gemini_for_content": true
}
```

### 4. Test Integration

```bash
python test_integration.py
```

Expected output:
```
🧪 Novel Crawler - Integration Test

============================================================
Testing Gemini API Connection
============================================================
✓ API Key found: AIzaSyBxxx...xxxxx
✓ Gemini client initialized successfully

------------------------------------------------------------
Testing Description Translation
------------------------------------------------------------
✓ Description translated with Gemini

------------------------------------------------------------
Testing Chapter Content Translation
------------------------------------------------------------
✓ Chapter translation successful

============================================================
✅ All tests passed! Gemini integration is working.
============================================================

============================================================
Testing WordPress API Connection
============================================================
✓ WordPress URL: http://volarenewnovels.local
✓ API Key: Fr9yOke8qh...W0Cb
✓ Connected to WordPress v6.x
✓ PHP v8.x

✅ WordPress connection successful!

============================================================
Test Summary
============================================================
Gemini API:     ✅ PASS
WordPress API:  ✅ PASS

🎉 All systems operational! Ready to crawl novels.

Try crawling a test novel:
  python crawler.py https://www.xbanxia.cc/books/396508.html
```

### 5. Crawl a Test Novel

Start with the 6-chapter test novel:

```bash
python crawler.py https://www.xbanxia.cc/books/396508.html
```

### 6. Check WordPress

Visit: http://volarenewnovels.local/wp-admin

You should see:
- ✅ Novel story with Gemini-translated description
- ✅ 6 chapters with glossary-consistent translations
- ✅ Character names consistent across all chapters

---

## 📋 What Changed

### Translation System

| Content Type | Before | After |
|--------------|--------|-------|
| **Novel Title** | Google Translate | ✅ Google Translate (unchanged) |
| **Novel Description** | Google Translate | ✅ **Gemini AI** (with cleanup prompt) |
| **Chapter Title** | Google Translate | ✅ Google Translate (unchanged) |
| **Chapter Content** | Google Translate | ✅ **Gemini AI** (with glossary) |

### New Workflow

**OLD (Single-Pass):**
1. Download chapter → Translate → Upload → Repeat

**NEW (Two-Pass with Glossary):**
1. **Pass 1:** Download ALL chapters
2. **Pass 2:** Generate glossary from first 10 chapters
3. **Pass 3:** Translate each chapter using glossary
4. **Pass 4:** Upload to WordPress

**Benefits:**
- ✅ Consistent character names across chapters
- ✅ Better context understanding
- ✅ Higher quality translations
- ✅ Automatic fallback to Google Translate on safety errors

---

## 🛠️ Configuration Options

### `config.json` Parameters

```json
{
  "wordpress_url": "http://volarenewnovels.local",
  "api_key": "Fr9yOke8qhGvVthc65gp0CQVvacrW0Cb",
  
  // NEW: Gemini API key
  "gemini_api_key": "YOUR_KEY_HERE",
  
  // NEW: Enable/disable Gemini for content
  "use_gemini_for_content": true,
  
  // Existing settings
  "max_chapters_per_run": 999,
  "delay_between_requests": 2,
  "translate": true,
  "target_language": "en"
}
```

### Environment Variable (Alternative)

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY="YOUR_KEY_HERE"
python crawler.py https://www.xbanxia.cc/books/396508.html
```

---

## 📊 Translation Quality Comparison

### Example Output

**Google Translate (OLD):**
> "Lin Feather stood at the mountain gate of the Azure Cloud Sect..."

**Gemini with Glossary (NEW):**
> "Lin Yu stood at the entrance of Azure Cloud Sect..."

Character name stays consistent throughout all chapters!

---

## 🔧 Troubleshooting

### Error: "No Gemini API key found"

**Solution:** Add your API key to `config.json`

### Error: "Gemini safety filter triggered"

**Solution:** The crawler automatically falls back to Google Translate. No action needed.

### Error: "ModuleNotFoundError: No module named 'google.genai'"

**Solution:**
```bash
pip install --upgrade google-genai
```

### Error: "WordPress connection failed"

**Solution:** Make sure your local WordPress is running:
- URL: http://volarenewnovels.local
- Check WordPress is accessible in browser

---

## 📁 Output Files

After crawling, check these locations:

### Local Files
```
crawler/crawler/novels/novel_396508/
├── metadata.json              # Novel info + translations
├── glossary.json              # NEW: Character/term glossary
├── cover.jpg                  # Cover image
├── chapters_raw/              # Original Chinese
│   └── 韶華三思_Chapter_001.html
└── chapters_translated/       # NEW: Gemini translations
    └── Think_twice_about_your_youth_Chapter_001.html
```

### WordPress
- Go to: http://volarenewnovels.local/wp-admin
- Posts → Stories → Check the novel
- Posts → Chapters → Check chapters

---

## 💡 Tips

1. **Start Small** - Test with 1 novel (6 chapters) first
2. **Check Quality** - Read a few translated chapters on WordPress
3. **Edit Glossary** - Manually edit `glossary.json` if you want different translations
4. **Monitor API Usage** - Gemini free tier has limits (15 req/min)
5. **Use Resume** - If interrupted, just run the same command again

---

## 🎯 Next Steps

After successful test:

1. **Crawl more novels:**
   ```bash
   python crawler.py https://www.xbanxia.cc/books/396941.html
   ```

2. **Crawl entire categories:**
   ```bash
   python crawler.py https://www.xbanxia.cc/list/1_1.html
   ```

3. **Adjust chapter limits:**
   - Edit `max_chapters_per_run` in config.json
   - Run crawler multiple times to resume

---

## 📞 Support

If you encounter issues:

1. **Check test output:**
   ```bash
   python test_integration.py
   ```

2. **Check crawler logs:**
   - Look for error messages in terminal
   - Check WordPress logs in plugin admin

3. **Verify API keys:**
   - Gemini: https://aistudio.google.com/app/apikey
   - WordPress: http://volarenewnovels.local/wp-admin (Novel Crawler menu)

---

**You're all set! Happy crawling! 🎉**
