import streamlit as st
from langdetect import detect, DetectorFactory
from langcodes import Language
import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import time
from ollama import Client
import datetime

# Agar deteksi bahasa konsisten
DetectorFactory.seed = 0

# Fungsi untuk menulis ke log virtual (tidak perlu file fisik)
def write_log(message, container=None):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    if container is not None:
        container.code(log_message)
    else:
        st.sidebar.write(log_message)

# Membersihkan konten HTML
def clean_html_content(content):
    if not content:
        return ""
    content = content.replace("```html", "").replace("```", "")
    content = content.replace("```", "").strip()
    return content

# Baca API Key dari secrets Streamlit
try:
    OLLAMA_API_KEY = st.secrets["OLLAMA_API_KEY"]
except KeyError:
    st.error("🔑 Missing Ollama API key in Streamlit Secrets!")
    st.stop()

# Konfigurasi Ollama Client
client = Client(
    host='https://ollama.com',
    headers={'Authorization': 'Bearer ' + OLLAMA_API_KEY}
)

MODEL_NAME = "gemma3:4b"

# Fungsi untuk mengirim permintaan ke model LLM
def call_llm(prompt, log_container=None):
    try:
        if log_container:
            write_log("→ Mengirim request ke LLM...", log_container)
        messages = [{'role': 'user', 'content': prompt}]
        response = client.chat(model=MODEL_NAME, messages=messages)
        result = response.message.content.strip()
        if log_container:
            write_log(f"→ Berhasil menerima response ({len(result)} karakter)", log_container)
        return result
    except Exception as e:
        error_msg = f"Gagal memanggil LLM: {str(e)}"
        if log_container:
            write_log(f"❌ ERROR: {error_msg}", log_container)
        raise Exception(error_msg)

# Deteksi bahasa
def detect_language(subject, log_container=None):
    try:
        if log_container:
            write_log(f"→ Mendeteksi bahasa untuk: {subject}", log_container)
        lang_code = detect(subject)
        lang_name = Language.get(lang_code).display_name()
        if log_container:
            write_log(f"→ Bahasa terdeteksi: {lang_name}", log_container)
        return lang_name
    except Exception:
        return "English"

# Generate Judul SEO Friendly
def generate_title(subject, language, log_container=None):
    if log_container:
        write_log(f"📝 Generating SEO title for: {subject}", log_container)
    title_prompt = (
        f"You are an expert SEO copywriter who creates compelling, click-worthy blog titles. "
        f"Create exactly ONE highly optimized SEO blog title for the topic: \"{subject}\". "
        f"The title must be between 50-60 characters, include primary keyword, and have strong search intent. "
        f"Language: {language}. Return ONLY the title, nothing else."
    )
    return call_llm(title_prompt, log_container)

# Generate Artikel Panjang dengan SEO Optimization
def generate_seo_article(title, subject, language, log_container=None):
    if log_container:
        write_log(f"📄 Generating comprehensive article (~10K+ chars)...", log_container)
        write_log(f"   Title: {title}", log_container)
        write_log(f"   Subject: {subject}", log_container)
        write_log(f"   Language: {language}", log_container)

    article_prompt = (
        f"You are an expert SEO content writer creating comprehensive, authoritative content. "
        f"Write a complete, in-depth blog article about \"{subject}\" with the title \"{title}\". "
        f"Requirements:\n"
        f"- Target length: 10,000+ words/characters (very comprehensive)\n"
        f"- Language: {language}\n"
        f"- SEO optimized with natural keyword placement\n"
        f"- Use only HTML tags: <h1>, <h2>, <h3>, <h4>, <p>, <ul>, <ol>, <li>, <strong>, <em>, <br>\n"
        f"- No markdown, no markdown tables\n"
        f"- Structure: Introduction → Main sections with H2/H3 → Conclusion\n"
        f"- Include semantic keywords naturally\n"
        f"- Add FAQ section at the end with 5-7 relevant questions\n"
        f"- Use descriptive, engaging paragraphs\n"
        f"- Bold important terms with <strong>\n"
        f"- Create natural content flow without forced keyword stuffing\n"
        f"- Focus on user search intent and provide valuable information\n\n"
        f"Return ONLY the complete HTML content, starting with <h1> and ending with final content."
    )
    return call_llm(article_prompt, log_container)

# Pencarian Gambar via Bing
def bing_image_search(query, log_container=None):
    try:
        if log_container:
            write_log(f"🖼️ Searching images for: {query}", log_container)

        query = '+'.join(query.split())
        url = f"http://www.bing.com/images/search?q={query}&FORM=HDRSC2"
        header = {'User-Agent': "Mozilla/5.0"}
        soup = BeautifulSoup(requests.get(url, headers=header).content, "html.parser")
        image_results_raw = soup.find_all("a", {"class": "iusc"})[:20]

        image_html_list = []
        if log_container:
            write_log(f"   Found {len(image_results_raw)} images, processing top 20...", log_container)

        for i, image_result_raw in enumerate(image_results_raw):
            try:
                m = json.loads(image_result_raw["m"])
                murl = m["murl"]
                mdesc = m.get("desc", f"Illustration related to {query}")
                image_name = urllib.parse.urlsplit(murl).path.split("/")[-1]
                image_html_list.append(
                    f'<div class="image-container">'
                    f'<img src="{murl}" alt="{image_name}" loading="lazy" width="600" height="400">'
                    f'<div class="image-caption">{mdesc}</div>'
                    f'</div>'
                )

                if log_container and i < 5:
                    write_log(f"   ✓ Processed image {i+1}: {image_name[:30]}...", log_container)

            except Exception as e:
                continue

        if log_container:
            write_log(f"   Successfully processed {len(image_html_list)} images", log_container)

        return image_html_list
    except Exception as e:
        error_msg = f"Error dalam pencarian gambar: {str(e)}"
        if log_container:
            write_log(f"   ❌ ERROR: {error_msg}", log_container)
        return [f"<p>Error dalam pencarian gambar: {str(e)}</p>"]

# Gabungkan Semua Proses Menjadi Satu
def generate_seo_article_with_images(subject, log_container=None):
    if log_container:
        write_log(f"🚀 STARTING ARTICLE GENERATION PROCESS", log_container)
        write_log(f"   Subject: {subject}", log_container)
        write_log("=" * 50, log_container)

    try:
        language = detect_language(subject, log_container)
        title = generate_title(subject, language, log_container)
        article = generate_seo_article(title, subject, language, log_container)

        if len(article) < 5000:
            if log_container:
                write_log("   ⚠️ Article too short, retrying...", log_container)
            article = generate_seo_article(title, subject, language, log_container)

        image_html_list = bing_image_search(subject, log_container)

        sections = article.split('<h2>')
        if len(sections) > 1:
            sections[0] += ' <span><!--more--></span>'
            for i, image_html in enumerate(image_html_list[:15]):
                section_index = min(i + 1, len(sections) - 1)
                if section_index < len(sections):
                    sections[section_index] = image_html + sections[section_index]
            article = '<h2>'.join(sections)
        else:
            article = ' <span><!--more--></span>'.join([sections[0]] + image_html_list[:3]) + ('<h2>' + '</h2><h2>'.join(sections[1:]) if len(sections) > 1 else '')

        if log_container:
            write_log(f"✅ ARTICLE GENERATION COMPLETED SUCCESSFULLY", log_container)
            write_log(f"   Final article length: {len(article):,} characters", log_container)
            write_log(f"   Images inserted: {min(15, len(image_html_list))}", log_container)
            write_log("=" * 50, log_container)

        return {"title": title, "article": article, "images": image_html_list[:15], "word_count": len(article)}

    except Exception as e:
        error_msg = str(e)
        if log_container:
            write_log(f"❌ FATAL ERROR IN ARTICLE GENERATION: {error_msg}", log_container)
        return {"error": error_msg}

# Template HTML untuk output
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="{'id' if 'Indonesia' in detect_language(subject, None) else 'en'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Complete guide about {subject}. Comprehensive information and insights.">
    <meta name="keywords" content="{subject}, guide, information, complete guide">
    <title>{title}</title>
    <style>
        body {{ font-family: Georgia, serif; line-height: 1.7; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; background-color: #fff; }}
        h1, h2, h3, h4 {{ color: #2c3e50; margin-top: 1.5em; margin-bottom: 0.8em; }}
        h1 {{ font-size: 2.2em; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ font-size: 1.8em; border-left: 4px solid #3498db; padding-left: 15px; }}
        h3 {{ font-size: 1.4em; }}
        p {{ margin-bottom: 1.2em; text-align: justify; }}
        .image-container {{ text-align: center; margin: 30px 0; padding: 15px; background-color: #f8f9fa; border-radius: 8px; }}
        img {{ max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .image-caption {{ font-size: 0.9em; color: #666; font-style: italic; margin-top: 10px; }}
        ul, ol {{ margin: 1em 0; padding-left: 2em; }}
        li {{ margin-bottom: 0.5em; }}
        strong {{ color: #2c3e50; }}
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            h1 {{ font-size: 1.8em; }}
            h2 {{ font-size: 1.5em; }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>
"""

# Halaman Utama Streamlit
st.set_page_config(page_title="SEO Article Generator", layout="wide")
st.title("🤖 SEO Article Generator (AI-Powered)")
st.subheader("Generate Long-form Articles Automatically using AI & Ollama Cloud")

with st.expander("ℹ️ How to use this tool"):
    st.markdown("""
    - Enter your topic below.
    - Click **Generate Article**.
    - Wait while we generate a full-length, SEO-friendly article with images.
    - Download the generated `.html` file or view it directly!
    """)

# Sidebar untuk logging
log_container = st.sidebar.container()

subject = st.text_input("Enter the main topic of the article:", placeholder="e.g., Benefits of Renewable Energy")

if st.button("🚀 Generate Article"):
    if not subject:
        st.warning("⚠️ Please enter a valid topic.")
    else:
        with st.spinner("⏳ Generating article... This may take up to 1 minute."):
            result = generate_seo_article_with_images(subject, log_container)

        if "error" in result:
            st.error(f"❌ Error generating article: {result['error']}")
        else:
            title = result["title"]
            article_content = result["article"]
            word_count = result.get("word_count", len(article_content))

            st.success(f"✅ Article generated successfully ({word_count:,} characters)!")

            # Render HTML langsung di halaman
            full_html = HTML_TEMPLATE.format(title=title, content=article_content, subject=subject)
            st.components.v1.html(full_html, height=1200, scrolling=True)

            # Tombol download
            st.download_button(
                label="📥 Download Full HTML",
                data=full_html,
                file_name=f"{subject.replace(' ', '_')}_article.html",
                mime="text/html"
            )
