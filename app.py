from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import logging
from playwright.sync_api import sync_playwright

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/91.0.4472.124 Safari/537.36'
    )
}

def is_valid_url(url):
    return url.startswith(('http://', 'https://'))

def normalize_key(key):
    key = key.lower().strip()
    mapping = {
        'memory': 'RAM',
        'ram': 'RAM',
        'internal storage': 'Storage',
        'storage': 'Storage',
        'battery capacity': 'Battery',
        'battery': 'Battery',
        'camera': 'Camera',
        'main camera': 'Camera',
        'display': 'Display',
        'screen size': 'Display',
        'price': 'Price',
        'product': 'Product'
    }
    for k in mapping:
        if k in key:
            return mapping[k]
    return key.title()

def scrape_dynamic_features(url):
    try:
        logger.info(f"Dynamic scraping: {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)

            data = {}

            if 'amazon' in url:
                title = page.query_selector('#productTitle')
                price = page.query_selector('.a-price .a-offscreen')
                specs = page.query_selector_all('#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr')

                data['Product'] = title.inner_text().strip() if title else 'N/A'
                data['Price'] = price.inner_text().strip() if price else 'N/A'

                for spec in specs:
                    key_el = spec.query_selector('th')
                    val_el = spec.query_selector('td')
                    if key_el and val_el:
                        key = normalize_key(key_el.inner_text().strip())
                        val = val_el.inner_text().strip()
                        data[key] = val

            elif 'flipkart' in url:
                title = page.query_selector('span.B_NuCI')
                price = page.query_selector('div._30jeq3._16Jk6d')
                specs = page.query_selector_all('div._1UhVsV > div')

                data['Product'] = title.inner_text().strip() if title else 'N/A'
                data['Price'] = price.inner_text().strip() if price else 'N/A'

                for section in specs:
                    rows = section.query_selector_all('tr')
                    for row in rows:
                        cells = row.query_selector_all('td')
                        if len(cells) == 2:
                            key = normalize_key(cells[0].inner_text().strip())
                            val = cells[1].inner_text().strip()
                            data[key] = val

            else:
                browser.close()
                return {'error': 'Unsupported platform'}

            browser.close()
            logger.info(f"Scraped {len(data)} features from {url}")
            return data

    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return {'error': f'Error scraping {url}: {str(e)}'}

@app.route('/compare', methods=['POST'])
def compare():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON payload'}), 400

    url1, url2 = data.get('url1'), data.get('url2')
    if not (url1 and url2):
        return jsonify({'error': 'Both URLs are required'}), 400
    if not (is_valid_url(url1) and is_valid_url(url2)):
        return jsonify({'error': 'URLs must start with http:// or https://'}), 400

    logger.info(f"Comparing: {url1} vs {url2}")
    result1 = scrape_dynamic_features(url1) if 'amazon' in url1 or 'flipkart' in url1 else scrape_features(url1)
    result2 = scrape_dynamic_features(url2) if 'amazon' in url2 or 'flipkart' in url2 else scrape_features(url2)

    if 'error' in result1:
        return jsonify({'error': result1['error']}), 400
    if 'error' in result2:
        return jsonify({'error': result2['error']}), 400

    return jsonify({'data1': result1, 'data2': result2})

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

@app.route('/')
def home():
    return jsonify({
        'name': 'Universal Feature Comparator API',
        'version': '1.1.0',
        'endpoints': {
            '/compare': 'POST - Compare features from two URLs',
            '/health': 'GET - Health check'
        }
    })

def scrape_features(url):
    try:
        logger.info(f"Scraping: {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        features = {}

        # Title
        title = soup.find('h1')
        if title:
            features['Product'] = title.get_text(strip=True)

        # Price
        price = extract_text(soup, PRICE_SELECTORS, 'Price')
        if price:
            features['Price'] = price

        # Description
        description = extract_text(soup, DESC_SELECTORS, 'Description')
        if not description:
            meta = soup.find('meta', attrs={'name': 'description'})
            content = meta.get('content', '') if meta else None
            if isinstance(content, str):
                description = content[:200] + "..."
            else:
                description = "No description found"
        features['Description'] = description

        # Feature lists
        if len(features) <= 1:
            import bs4
            for i, ul in enumerate(soup.find_all(['ul', 'ol'])[:3]):
                if isinstance(ul, bs4.element.Tag):
                    items = [li.get_text(strip=True) for li in ul.find_all('li')[:5]]
                    if items:
                        features[f'Feature List {i+1}'] = ', '.join(items)

        # Fallback
        if not features:
            page_title = soup.find('title')
            features = {
                'Title': page_title.get_text(strip=True) if page_title else 'No title found',
                'URL': url,
                'Content Length': f"{len(response.content)} bytes"
            }

        logger.info(f"Scraped {len(features)} features from {url}")
        return features

    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        return {'error': f'Failed to fetch {url}: {str(e)}'}
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return {'error': f'Error scraping {url}: {str(e)}'}

@app.route('/compare', methods=['POST'])
def compare():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON payload'}), 400

    url1, url2 = data.get('url1'), data.get('url2')
    if not (url1 and url2):
        return jsonify({'error': 'Both URLs are required'}), 400
    if not (is_valid_url(url1) and is_valid_url(url2)):
        return jsonify({'error': 'URLs must start with http:// or https://'}), 400

    logger.info(f"Comparing: {url1} vs {url2}")
    result1, result2 = scrape_features(url1), scrape_features(url2)

    if 'error' in result1:
        return jsonify({'error': result1['error']}), 400
    if 'error' in result2:
        return jsonify({'error': result2['error']}), 400

    return jsonify({'data1': result1, 'data2': result2})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'API is running'})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'name': 'Universal Feature Comparator API',
        'version': '1.1.0',
        'endpoints': {
            '/compare': 'POST - Compare features from two URLs',
            '/health': 'GET - Health check'
        }
    })



@app.route('/meta')
def meta():
    return jsonify({
        "endpoints": {
            "compare": "POST - Compare features from two URLs",
            "health": "GET - Health check"
        },
        "name": "Universal Feature Comparator API",
        "version": "1.0.0"
    })

# if __name__ == '__main__':
#     logger.info("Starting Universal Feature Comparator API...")
#     app.run(debug=True, host='0.0.0.0', port=5000)


