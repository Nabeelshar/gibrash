# Gemini AI Translation Setup

## Overview

This enhanced crawler now uses **Gemini 1.5 Flash & 2.5 Flash** for intelligent translation with these features:

✅ **Google Translate** - For novel titles and chapter titles (fast, accurate for short text)  
✅ **Gemini AI** - For novel descriptions and chapter content (intelligent, context-aware)  
✅ **Glossary System** - Analyzes ALL downloaded chapters to generate consistent character names and terms  
✅ **Automatic Fallback** - Falls back to Google Translate if Gemini safety filters trigger  

---

## 🔑 Getting Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **"Get API Key"**
3. Create a new project or select existing
4. Copy your API key

---

## ⚙️ Configuration

### Method 1: Edit `config.json`

```json
{
  "wordpress_url": "http://volarenewnovels.local",
  "api_key": "Fr9yOke8qhGvVthc65gp0CQVvacrW0Cb",
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
  "max_chapters_per_run": 999,
  "translate": true,
  "use_gemini_for_content": true
}
```

### Method 2: Environment Variable (Recommended for Security)

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

**Windows CMD:**
```cmd
set GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

---

## 📦 Installation

```bash
cd "crawler/crawler"
pip install -r requirements.txt
```

This installs:
- `google-genai` - Gemini API client
- `googletrans==4.0.0rc1` - Free Google Translate (for titles and fallback)
- `requests`, `beautifulsoup4`, `lxml` - Web scraping

---

## 🚀 Usage

### Crawl a Single Novel

```bash
python crawler.py https://www.xbanxia.cc/books/396941.html
```

### Crawl a Category

```bash
python crawler.py https://www.xbanxia.cc/list/1_1.html
```

---

## 🔄 How It Works

### **Translation Workflow**

1. **Novel Metadata:**
   - **Title** → Google Translate (fast, accurate)
   - **Description** → Gemini AI with prompt to remove extra content

2. **Chapter Processing (Two-Pass System):**
   
   **PASS 1: Download All Chapters**
   - Downloads all raw Chinese chapters
   - Saves to `chapters_raw/`
   
   **PASS 2: Generate Glossary**
   - Analyzes ALL downloaded chapters (complete content)
   - Extracts character names, places, and terms
   - Creates consistent English translations using Gemini 2.5 Flash
   - Saves to `glossary.json`
   
   **PASS 3: Translate with Glossary**
   - **Chapter Title** → Google Translate
   - **Chapter Content** → Gemini 1.5 Flash with glossary for consistency
   - **On Gemini Failure** → Automatic fallback to Google Translate
   - Saves to `chapters_translated/`
   
   **PASS 4: Upload to WordPress**
   - Posts translated chapters via REST API

---

## 🛡️ Safety Filter Handling

Gemini has content safety filters. When triggered:

```
⚠ Gemini safety filter triggered: SAFETY
⚠ Gemini failed, falling back to Google Translate...
✓ Content translated with Google Translate
```

This ensures **no chapter is ever skipped** due to content restrictions.

---

## 📁 File Structure

After crawling, you'll have:

```
novels/
└── novel_396941/
    ├── metadata.json              # Novel info with translations
    ├── glossary.json               # Character names & terms (NEW!)
    ├── cover.jpg                   # Downloaded cover
    ├── chapters_raw/               # Original Chinese
    │   ├── 小说名_Chapter_001.html
    │   └── ...
    └── chapters_translated/        # Gemini-translated English
        ├── Novel_Name_Chapter_001.html
        └── ...
```

---

## 💡 Configuration Options

### `config.json` Parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `gemini_api_key` | `""` | Your Gemini API key |
| `use_gemini_for_content` | `true` | Use Gemini for descriptions/chapters |
| `translate` | `true` | Enable/disable translation |
| `max_chapters_per_run` | `999` | Chapters per execution |
| `delay_between_requests` | `2` | Seconds between requests |

---

## 🧪 Testing

### Test Novel (6 chapters):

```bash
python crawler.py https://www.xbanxia.cc/books/396508.html
```

Check WordPress at: http://volarenewnovels.local/wp-admin

Expected output:
```
[1/6] Testing WordPress API connection...
  Connected (WordPress v6.x)

[2/6] Fetching novel page...
  Fetched (xxx bytes)

[3/6] Parsing novel data...
  Title: 韶華三思
  Chapters found: 6

[4/6] Translating metadata...
  Title (EN - Google Translate): Think Twice About Your Youth
  Description (EN - Gemini): Translated & cleaned

[5/6] Checking if story exists...
  Story created (ID: 123)

[6/6] Processing chapters (max 999)...

  ==================================================
  PASS 1: Downloading raw chapters
  ==================================================
    Chapter 1: Downloading...
      Extracted 3521 characters
      Saved to 韶華三思_Chapter_001.html
    ...

  ==================================================
  PASS 2: Generating glossary and translating
  ==================================================
  
Generating Translation Glossary
==================================================
Analyzing all 6 chapters (complete raw content)...
  Using complete content (21089 chars, ~5272 tokens)
✓ Glossary generated with 25 entries
  - Characters: 8
  - Places: 5
  - Terms: 12

  Sample glossary entries:
    林羽 → Lin Yu
    青云宗 → Azure Cloud Sect
    ...

    Chapter 1: Translating...
      Title: Chapter 1 (Google Translate)
      Attempting Gemini translation...
      ✓ Content translated with Gemini (4523 chars)
      Saved to Think_twice_about_your_youth_Chapter_001.html
      Uploading to WordPress...
      ✓ Created in WordPress (ID: 456)
```

---

## 🔧 Troubleshooting

### ❌ "Gemini client initialization failed"

**Solution:** Install the Gemini SDK:
```bash
pip install --upgrade google-genai
```

### ❌ "Invalid API key"

**Solution:** Check your Gemini API key at https://aistudio.google.com/app/apikey

### ❌ "All chapters translated with Google Translate"

**Possible causes:**
1. `gemini_api_key` not set in config.json
2. `use_gemini_for_content` set to `false`
3. Gemini API quota exceeded (check [quotas](https://aistudio.google.com/app/quotas))

### ❌ Rate limit errors

**Solution:** Gemini free tier has limits:
- 15 requests per minute
- 1 million tokens per minute
- 1,500 requests per day

Add delays or use paid tier for heavy usage.

---

## 💰 Pricing

### Gemini 1.5 Flash (gemini-flash-latest):
- **Free Tier:** 15 RPM, 1M TPM, 1,500 requests/day
- **Paid Tier:** Input: $0.075/$1M tokens, Output: $0.30/$1M tokens

### Gemini 2.5 Flash (for glossary generation):
- **Free Tier:** 10 RPM, 4M TPM, 1,500 requests/day  
- **Paid Tier:** Input: $0.075/$1M tokens, Output: $0.30/$1M tokens

### Google Translate (via googletrans):
- **100% Free** - Uses public API

**Note:** Free tier limits are generous for testing, but heavy crawling may require paid tier.

---

## 📊 Performance Comparison

| Aspect | Google Translate | Gemini 1.5 Flash | Gemini 2.5 Flash |
|--------|-----------------|------------------|------------------|
| **Speed** | ⚡ Fast (1s) | 🐢 Slower (5-10s) | 🐢 Slower (5-10s) |
| **Quality** | ✓ Good for titles | ✅ Excellent for content | ✅ Best for analysis |
| **Consistency** | ❌ No context | ✅ Glossary-aware | ✅ Best for glossary |
| **Cost** | 💰 Free | 💰 $0.075-0.30/$1M | 💰 $0.075-0.30/$1M |
| **Content Filtering** | ✅ None | ⚠️ Has safety filters | ⚠️ Has safety filters |
| **Use Case** | Titles, fallback | Chapter translation | Glossary generation |

---

## 🎯 Best Practices

1. **Start Small** - Test with 1 novel first
2. **Monitor Output** - Check translated quality on WordPress
3. **Adjust Glossary** - Edit `glossary.json` manually if needed
4. **Use Resume** - Crawler automatically resumes interrupted novels
5. **Batch Processing** - Set `max_chapters_per_run` for incremental crawling

---

## 📝 Example Glossary (Auto-Generated)

```json
{
  "characters": {
    "林羽": "Lin Yu",
    "苏倾城": "Su Qingcheng",
    "李长老": "Elder Li"
  },
  "places": {
    "青云宗": "Azure Cloud Sect",
    "天元城": "Tianyuan City"
  },
  "terms": {
    "筑基期": "Foundation Establishment",
    "金丹": "Golden Core",
    "灵气": "Spiritual Energy"
  }
}
```

---

## 🔗 Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Get API Key](https://aistudio.google.com/app/apikey)
- [Pricing](https://ai.google.dev/pricing)
- [Usage Limits](https://ai.google.dev/docs/usage_limits)

---

## ✨ Features Summary

- ✅ Dual translation system (Google Translate + Gemini)
- ✅ Intelligent glossary generation
- ✅ Automatic safety filter fallback
- ✅ Resume interrupted crawls
- ✅ Progress tracking
- ✅ Cached translations
- ✅ WordPress REST API integration
- ✅ Zero cost (free tier)
