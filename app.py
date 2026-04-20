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

# Fungsi untuk menulis ke log virtual
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
def generate_title(subject, language, tone_style, log_container=None):
    if log_container:
        write_log(f"📝 Generating SEO title for: {subject}", log_container)
    title_prompt = (
        f"You are an expert SEO copywriter who creates compelling, click-worthy blog titles. "
        f"Create exactly ONE highly optimized SEO blog title for the topic: \"{subject}\". "
        f"The title must be between 50-60 characters, include primary keyword, and have strong search intent. "
        f"Tone Style: {tone_style}. "
        f"Language: {language}. Return ONLY the title, nothing else."
    )
    return call_llm(title_prompt, log_container)

# Generate Artikel Panjang dengan SEO Optimization
def generate_seo_article(title, subject, language, tone_style, article_length, log_container=None):
    if log_container:
        write_log(f"📄 Generating comprehensive article (~{article_length} chars)...", log_container)
        write_log(f"   Title: {title}", log_container)
        write_log(f"   Subject: {subject}", log_container)
        write_log(f"   Language: {language}", log_container)
        write_log(f"   Tone Style: {tone_style}", log_container)

    char_target = {
        "pendek": 3000,
        "sedang": 7000,
        "panjang": 10000
    }[article_length.lower()]

    article_prompt = (
        f"You are an expert SEO content writer creating comprehensive, authoritative content. "
        f"Write a complete, in-depth blog article about \"{subject}\" with the title \"{title}\". "
        f"Requirements:\n"
        f"- Target length: ~{char_target} characters\n"
        f"- Language: {language}\n"
        f"- Tone Style: {tone_style}\n"
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
def bing_image_search(query, num_images=10, log_container=None):
    try:
        if log_container:
            write_log(f"🖼️ Searching images for: {query} (limit: {num_images})", log_container)

        query = '+'.join(query.split())
        url = f"http://www.bing.com/images/search?q={query}&FORM=HDRSC2"
        header = {'User-Agent': "Mozilla/5.0"}
        soup = BeautifulSoup(requests.get(url, headers=header).content, "html.parser")
        image_results_raw = soup.find_all("a", {"class": "iusc"})[:num_images]

        image_html_list = []
        if log_container:
            write_log(f"   Found {len(image_results_raw)} images, processing top {num_images}...", log_container)

        for i, image_result_raw in enumerate(image_results_raw):
            try:
                m = json.loads(image_result_raw["m"])
                murl = m["murl"]
                mdesc = m.get("desc", f"Illustration related to {query}")
                image_name = urllib.parse.urlsplit(murl).path.split("/")[-1]
                image_html_list.append(
                    f'<div class="image-container">'
                    f'<img src="{murl}" alt="{image_name}" loading="lazy" width="600" height="400">'
                    f'<div class="image-caption"><small>{mdesc}</small></div>'
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
def generate_seo_article_with_images(subject, settings, log_container=None):
    if log_container:
        write_log(f"🚀 STARTING ARTICLE GENERATION PROCESS", log_container)
        write_log(f"   Subject: {subject}", log_container)
        write_log("=" * 50, log_container)

    try:
        language = detect_language(subject, log_container)
        title = generate_title(subject, language, settings["tone"], log_container)
        article = generate_seo_article(title, subject, language, settings["tone"], settings["length"], log_container)

        image_html_list = bing_image_search(subject, settings["image_count"], log_container)

        sections = article.split('<h2>')
        if len(sections) > 1:
            sections[0] += ' <span><!--more--></span>'
            insert_positions = list(range(1, min(len(sections), settings["image_count"] + 1)))
            for i, image_html in enumerate(image_html_list[:settings["image_count"]]):
                pos = insert_positions[i % len(insert_positions)]
                if pos < len(sections):
                    sections[pos] = image_html + sections[pos]
            article = '<h2>'.join(sections)
        else:
            article = ' <span><!--more--></span>'.join([sections[0]] + image_html_list[:settings["image_count"]])

        if log_container:
            write_log(f"✅ ARTICLE GENERATION COMPLETED SUCCESSFULLY", log_container)
            write_log(f"   Final article length: {len(article):,} characters", log_container)
            write_log(f"   Images inserted: {min(settings['image_count'], len(image_html_list))}", log_container)
            write_log("=" * 50, log_container)

        return {"title": title, "article": article, "images": image_html_list[:settings["image_count"]], "word_count": len(article)}

    except Exception as e:
        error_msg = str(e)
        if log_container:
            write_log(f"❌ FATAL ERROR IN ARTICLE GENERATION: {error_msg}", log_container)
        return {"error": error_msg}

# Template HTML untuk output
def create_html_template(title, content, subject, theme="light"):
    html_lang = 'id' if 'Indonesia' in detect_language(subject, None) else 'en'
    
    bg_color = "#ffffff" if theme == "light" else "#1e1e1e"
    text_color = "#333333" if theme == "light" else "#e0e0e0"
    heading_color = "#2c3e50" if theme == "light" else "#ffffff"
    
    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Complete guide about {subject}. Comprehensive information and insights.">
    <meta name="keywords" content="{subject}, guide, information, complete guide">
    <title>{title}</title>
    <style>
        body {{ 
            font-family: Georgia, serif; 
            line-height: 1.7; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
            background-color: {bg_color}; 
            color: {text_color};
        }}
        h1, h2, h3, h4 {{ color: {heading_color}; margin-top: 1.5em; margin-bottom: 0.8em; }}
        h1 {{ font-size: 2.2em; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ font-size: 1.8em; border-left: 4px solid #3498db; padding-left: 15px; }}
        h3 {{ font-size: 1.4em; }}
        p {{ margin-bottom: 1.2em; text-align: justify; }}
        .image-container {{ 
            text-align: center; 
            margin: 30px 0; 
            padding: 15px; 
            background-color: {'#f8f9fa' if theme == 'light' else '#2d2d2d'}; 
            border-radius: 8px; 
        }}
        img {{ max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .image-caption {{ 
            font-size: 0.50em; 
            color: {'#666' if theme == 'light' else '#aaa'}; 
            font-style: italic; 
            margin-top: 10px; 
            line-height: 1.4;
        }}
        .image-caption small {{ 
            font-size: 0.50em; 
        }}
        ul, ol {{ margin: 1em 0; padding-left: 2em; }}
        li {{ margin-bottom: 0.5em; }}
        strong {{ color: {heading_color}; }}
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            h1 {{ font-size: 1.8em; }}
            h2 {{ font-size: 1.5em; }}
            .image-caption {{ font-size: 0.75em; }}
            .image-caption small {{ font-size: 0.75em; }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>"""

# Halaman Utama Streamlit
st.set_page_config(page_title="SEO Article Generator", layout="wide")
st.title("🤖 SEO Article Generator (AI-Powered)")
st.subheader("Generate Long-form Articles Automatically using AI & Ollama Cloud")

with st.expander("ℹ️ How to use this tool"):
    st.markdown("""
    - Enter your topic below.
    - Customize settings like tone, article length, number of images, etc.
    - Click **Generate Article**.
    - Wait while we generate a full-length, SEO-friendly article with images.
    - Download the generated `.html` file or view it directly!
    """)

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Pengaturan Artikel")
    tone_options = ["Formal", "Santai", "Lucu", "Profesional", "Inspiratif"]
    tone = st.selectbox("Gaya Bahasa/Tone", options=tone_options, index=0)
    length_options = ["Pendek (~3k)", "Sedang (~7k)", "Panjang (~10k+)"]
    length = st.radio("Panjang Artikel", options=length_options, index=2)
    image_count = st.slider("Jumlah Gambar", min_value=0, max_value=20, value=5)
    image_placement = st.selectbox("Posisi Gambar", options=["Acak", "Awal Artikel"], index=0)
    theme_options = ["Terang", "Gelap"]
    theme = st.radio("Tema Output", options=theme_options, index=0)
    submit_btn = st.button("🔄 Reset")

subject = st.text_input("Enter the main topic of the article:", placeholder="e.g., Benefits of Renewable Energy")

if st.button("🚀 Generate Article"):
    if not subject:
        st.warning("⚠️ Please enter a valid topic.")
    else:
        settings = {
            "tone": tone,
            "length": length.split()[0].lower(),
            "image_count": image_count,
            "placement": image_placement,
            "theme": "dark" if theme == "Gelap" else "light"
        }

        log_container = st.sidebar.container()
        with st.spinner("⏳ Generating article... This may take up to 1 minute."):
            result = generate_seo_article_with_images(subject, settings, log_container)

        if "error" in result:
            st.error(f"❌ Error generating article: {result['error']}")
        else:
            title = result["title"]
            article_content = result["article"]
            word_count = result.get("word_count", len(article_content))

            st.success(f"✅ Article generated successfully ({word_count:,} characters)!")

            # Render HTML langsung di halaman
            full_html = create_html_template(title, article_content, subject, settings["theme"])
            st.components.v1.html(full_html, height=1200, scrolling=True)

            # Tombol download
            st.download_button(
                label="📥 Download Full HTML",
                data=full_html,
                file_name=f"{subject.replace(' ', '_')}_article.html",
                mime="text/html"
            )
