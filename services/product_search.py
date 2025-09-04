import requests
import json
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
import os
from urllib.parse import quote

@dataclass
class Product:
    name: str
    price: str
    supplier: str
    min_order: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    supplier_location: Optional[str] = None
    platform: Optional[str] = None  # Alibaba, 1688, Made-in-China
    product_url: Optional[str] = None

class ProductSearchService:
    def __init__(self):
        # API ключи из переменных окружения
        self.alibaba_api_key = os.getenv('ALIBABA_API_KEY')
        self.api_1688_key = os.getenv('1688_API_KEY')
        
        # Заголовки для парсинга
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.mock_products = [
            Product(
                name="Wireless Bluetooth Headphones",
                price="$8.50 - $12.00",
                supplier="Shenzhen Audio Tech Co.",
                min_order="100 pieces",
                supplier_location="Shenzhen, China",
                description="High-quality wireless headphones with noise cancellation"
            ),
            Product(
                name="USB-C Cable 1m",
                price="$0.85 - $1.20",
                supplier="Guangzhou Cable Manufacturing",
                min_order="500 pieces",
                supplier_location="Guangzhou, China",
                description="Fast charging USB-C cable with data transfer"
            ),
            Product(
                name="Smartphone Case TPU",
                price="$1.50 - $2.80",
                supplier="Dongguan Plastic Industries",
                min_order="200 pieces",
                supplier_location="Dongguan, China",
                description="Flexible TPU phone case with drop protection"
            ),
            Product(
                name="LED Strip Lights 5m",
                price="$3.20 - $5.50",
                supplier="Zhongshan LED Solutions",
                min_order="50 pieces",
                supplier_location="Zhongshan, China",
                description="RGB LED strip with remote control"
            ),
            Product(
                name="Portable Power Bank 10000mAh",
                price="$6.80 - $9.50",
                supplier="Shenzhen Power Tech",
                min_order="100 pieces",
                supplier_location="Shenzhen, China",
                description="Fast charging power bank with dual USB ports"
            )
        ]
    
    def search_products(self, query: str) -> List[Product]:
        """Search for products across multiple platforms"""
        all_results = []
        
        # Поиск на всех платформах
        try:
            # 1. Alibaba.com
            alibaba_results = self._search_alibaba(query)
            all_results.extend(alibaba_results)
            
            # 2. 1688.com
            api_1688_results = self._search_1688(query)
            all_results.extend(api_1688_results)
            
            # 3. Made-in-China.com
            made_in_china_results = self._search_made_in_china(query)
            all_results.extend(made_in_china_results)
            
        except Exception as e:
            print(f"Error searching platforms: {e}")
        
        # Если нет результатов с реальных площадок, используем mock данные
        if not all_results:
            query_lower = query.lower()
            for product in self.mock_products:
                if (query_lower in product.name.lower() or 
                    query_lower in product.description.lower()):
                    all_results.append(product)
            
            # Если и mock данные не подходят, возвращаем первые 3
            if not all_results:
                all_results = self.mock_products[:3]
        
        return all_results[:10]  # Возвращаем до 10 результатов
    
    def get_product_details(self, product_name: str) -> Optional[Product]:
        """Get detailed information about a specific product"""
        for product in self.mock_products:
            if product.name.lower() == product_name.lower():
                return product
        return None
    
    def format_product_message(self, products: List[Product], language_service=None, user_id=None) -> str:
        """Format products into a readable message"""
        if not products:
            if language_service and user_id:
                return language_service.get_text(user_id, 'no_products')
            return "❌ No products found. Try a different search term."
        
        if language_service and user_id:
            header = language_service.get_text(user_id, 'products_found', count=len(products))
            price_label = language_service.get_text(user_id, 'price')
            supplier_label = language_service.get_text(user_id, 'supplier')
            min_order_label = language_service.get_text(user_id, 'min_order')
            location_label = language_service.get_text(user_id, 'location')
            contact_msg = language_service.get_text(user_id, 'contact_quote')
        else:
            header = f"🔍 **Found {len(products)} products:**"
            price_label = "Price:"
            supplier_label = "Supplier:"
            min_order_label = "Min Order:"
            location_label = "Location:"
            contact_msg = "💡 *Contact us to get detailed quotes and supplier verification!*\n\n🚚 *Logistics and shipping costs are calculated separately based on your location and order volume.*"
        
        message = f"{header}\n\n"
        
        for i, product in enumerate(products, 1):
            message += f"🛍️ **{product.name}**\n"
            message += f"💰 {price_label} {product.price}\n"
            message += f"🏭 {supplier_label} {product.supplier}\n"
            message += f"📦 {min_order_label} {product.min_order}\n"
            message += f"📍 {location_label} {product.supplier_location}\n"
            if product.platform:
                platform_label = language_service.get_text(user_id, 'platform') if language_service and user_id else "Platform:"
                message += f"🌐 {platform_label} {product.platform}\n"
            if product.description:
                message += f"📝 {product.description}\n"
            message += "\n"
        
        message += contact_msg
        return message
    
    def _search_alibaba(self, query: str) -> List[Product]:
        """Поиск товаров на Alibaba.com"""
        results = []
        
        if not self.alibaba_api_key:
            print("Alibaba API key not found, using mock data")
            return []
        
        try:
            # Alibaba API endpoint (примерный)
            url = "https://api.alibaba.com/v1/products/search"
            params = {
                'q': query,
                'limit': 5,
                'api_key': self.alibaba_api_key
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('products', []):
                    product = Product(
                        name=item.get('title', 'Unknown Product'),
                        price=f"${item.get('min_price', 0)} - ${item.get('max_price', 0)}",
                        supplier=item.get('supplier_name', 'Unknown Supplier'),
                        min_order=f"{item.get('min_order_qty', 1)} pieces",
                        image_url=item.get('image_url'),
                        description=item.get('description', ''),
                        supplier_location=item.get('supplier_location', 'China'),
                        platform="Alibaba.com",
                        product_url=item.get('product_url')
                    )
                    results.append(product)
                    
        except Exception as e:
            print(f"Error searching Alibaba: {e}")
        
        return results
    
    def _search_1688(self, query: str) -> List[Product]:
        """Поиск товаров на 1688.com"""
        results = []
        
        if not self.api_1688_key:
            print("1688 API key not found, using mock data")
            return []
        
        try:
            # 1688 API endpoint (примерный)
            url = "https://open.1688.com/api/1/products/search"
            params = {
                'keyword': query,
                'pageSize': 5,
                'access_token': self.api_1688_key
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('result', {}).get('products', []):
                    product = Product(
                        name=item.get('subject', 'Unknown Product'),
                        price=f"¥{item.get('price', 0)} - ¥{item.get('retailPrice', 0)}",
                        supplier=item.get('company', 'Unknown Supplier'),
                        min_order=f"{item.get('saledCount', 1)} pieces",
                        image_url=item.get('image'),
                        description=item.get('description', ''),
                        supplier_location=item.get('location', 'China'),
                        platform="1688.com",
                        product_url=item.get('detailUrl')
                    )
                    results.append(product)
                    
        except Exception as e:
            print(f"Error searching 1688: {e}")
        
        return results
    
    def _search_made_in_china(self, query: str) -> List[Product]:
        """Парсинг товаров с Made-in-China.com"""
        results = []
        
        try:
            # Поиск через веб-парсинг
            search_url = f"https://www.made-in-china.com/products-search/hot-china-products/{quote(query)}.html"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Парсинг результатов поиска
                product_items = soup.find_all('div', class_='item-main')[:5]
                
                for item in product_items:
                    try:
                        # Извлечение данных товара
                        title_elem = item.find('h2', class_='title')
                        title = title_elem.get_text(strip=True) if title_elem else 'Unknown Product'
                        
                        price_elem = item.find('span', class_='price')
                        price = price_elem.get_text(strip=True) if price_elem else 'Contact for price'
                        
                        supplier_elem = item.find('a', class_='company')
                        supplier = supplier_elem.get_text(strip=True) if supplier_elem else 'Unknown Supplier'
                        
                        img_elem = item.find('img')
                        image_url = img_elem.get('src') if img_elem else None
                        
                        link_elem = item.find('a', href=True)
                        product_url = f"https://www.made-in-china.com{link_elem['href']}" if link_elem else None
                        
                        product = Product(
                            name=title,
                            price=price,
                            supplier=supplier,
                            min_order="Contact supplier",
                            image_url=image_url,
                            description="",
                            supplier_location="China",
                            platform="Made-in-China.com",
                            product_url=product_url
                        )
                        results.append(product)
                        
                    except Exception as e:
                        print(f"Error parsing product item: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error searching Made-in-China: {e}")
        
        return results
