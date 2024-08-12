from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
from scraperapi_sdk import ScraperAPIClient, ScraperAPIException
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('query')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    discount_only = request.args.get('discount_only') == 'true'
    coupon_items = request.args.get('coupon_items') == 'true'

    page = int(request.args.get('page', '1'))

    amazon_associates_id = os.getenv('AMAZON_ASSOCIATES')
    
    if not query:
        return jsonify({"error": "Please provide a search query"}), 400

    try:
        products = []
        while True:
            url = f"https://www.amazon.com/s?k={query}&page={page}"
            scraperapi_client = ScraperAPIClient(os.getenv('SCRAPERAPI'))
            result = scraperapi_client.get(url=url)

            soup = BeautifulSoup(result, 'html.parser')

            new_products = []
            for item in soup.select('.s-main-slot .s-result-item'):
                title = item.select_one('h2 a span').text if item.select_one('h2 a span') else None
                price = item.select_one('.a-price .a-offscreen').text if item.select_one('.a-price .a-offscreen') else None
                image_url = item.select_one('img').get('src') if item.select_one('img') else None
                product_url = item.select_one('h2 a').get('href') if item.select_one('h2 a') else None

                # Detect if a discount percentage is available
                discount = item.select_one('.a-size-base .a-color-price')  # Adjust based on actual class

                # Detect if a coupon is available
                coupon = item.select_one('.couponBadge') or item.find(string=lambda text: 'coupon' in text.lower())

                if title and price and image_url and product_url:
                    price_value = float(price.replace('$', '').replace(',', ''))

                    if product_url.startswith('/'):
                        product_url = f"https://www.amazon.com{product_url}"

                    full_product_url = f"{product_url}?tag={amazon_associates_id}"

                    if min_price and price_value < float(min_price):
                        continue
                    if max_price and price_value > float(max_price):
                        continue
                    if discount_only and not discount:
                        continue
                    if coupon_items and not coupon:
                        continue
                    
                    new_products.append({
                        'title': title,
                        'price': price_value,
                        'image_url': image_url,
                        'product_url': full_product_url,
                        'promo_code': 'YES' if coupon else 'NO'
                    })

            if not new_products:
                break

            products.extend(new_products)
            page += 1

        products = sorted(products, key=lambda x: x['price'])

        return render_template('search_results.html', products=products, query=query, page=page-1, has_next_page=False)

    except ScraperAPIException as e:
        return jsonify({"error": "Failed to scrape Amazon. Please try again later."}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050)
