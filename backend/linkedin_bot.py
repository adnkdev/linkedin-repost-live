import time
import os, uuid, logging, requests, json, threading
from urllib.parse import urlencode,quote
from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote_plus

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:3000",
    "https://linkedin-repost-live-lcsf.vercel.app",
    "https://linkedin-repost-live-lcsf-6ic9b33ji-adnans-projects-fce256b2.vercel.app"
]}})

logging.basicConfig(level=logging.DEBUG)

CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID', '86lnmivch9tovy')# LinkedIn app client ID
CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET', 'WPL_AP1.qwBLnG8Wa3oYgVOp.4Cj07w==')# LinkedIn app client secret
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://linkedin-repost-live-lcsf.vercel.app/linkedin-callback')# Redirect URI for LinkedIn app
# Ensure the redirect URI is registered in your LinkedIn app settings
SCOPES = 'r_liteprofile r_emailaddress w_member_social'# Scopes for LinkedIn API access
# Ensure the scopes are registered in your LinkedIn app settings

VALID_STATES = set()

@app.route('/api/start_oauth')
def start_oauth():
    state = str(uuid.uuid4())
    VALID_STATES.add(state)
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'state': state,
        'scope': SCOPES
    }
    auth_url = 'https://www.linkedin.com/oauth/v2/authorization?' + urlencode(params, quote_via=quote)
    logging.info(f"Generated auth URL: {auth_url}")
    return jsonify({'authUrl': auth_url})

@app.route('/api/exchange_token', methods=['POST'])
def exchange_token():
    data = request.json or {}
    code = data.get('code')
    state = data.get('state')
    logging.info(f"Exchanging code={code} state={state}")

    if not code or not state or state not in VALID_STATES:
        return jsonify({'error': 'Invalid code or state'}), 400
    VALID_STATES.remove(state)

    token_resp = requests.post(
        'https://www.linkedin.com/oauth/v2/accessToken',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    logging.info(f"Token endpoint status: {token_resp.status_code}")
    if token_resp.status_code != 200:
        return jsonify({
            'error': 'Failed to get token',
            'details': token_resp.text
        }), 400

    token_data = token_resp.json()
    access_token = token_data.get('access_token')

    profile_resp = requests.get(
        'https://api.linkedin.com/v2/me?projection=(id,localizedFirstName,localizedLastName,profilePicture(displayImage~:playableStreams))',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    logging.info(f"Profile status: {profile_resp.status_code}")
    profile = profile_resp.ok and profile_resp.json()

    email_resp = requests.get(
        'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    logging.info(f"Email status: {email_resp.status_code}")
    email = email_resp.ok and email_resp.json()

    return jsonify({
        'access_token': access_token,
        'profile': profile,
        'email': email
    })


class LinkedInBot:
    def __init__(self, email, password, access_token, search_query):
        self.email = email
        self.password = password
        self.access_token = access_token
        self.search_query = search_query
        self.driver = None
        self.wait = None
        self.history_file = 'engagement_history.json'
        self.engagement_history = self._load_history()
        self.max_daily_posts = 10
        self.posts_today = 0
        self.last_reset = time.time()


    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed loading history: {e}")
        return {"posts": []}
    
    def _maybe_reset_daily_counter(self):
        now = time.time()
        if now - self.last_reset > 86400:  # 24 hours
            self.posts_today = 0
            self.last_reset = now
            logging.info("Daily post counter reset.")

    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.engagement_history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed saving history: {e}")

    def setup_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")  # Use modern headless mode
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });
        """
        })
        self.wait = WebDriverWait(self.driver, 20)

    def login(self):
        self.driver.get("https://www.linkedin.com/login")
        user = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        pwd = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
        user.send_keys(self.email)
        pwd.send_keys(self.password)
        pwd.send_keys(Keys.RETURN)
        time.sleep(20)
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "global-nav")))
            return True
        except TimeoutException:
            return False

    def find_top_post(self):
        encoded = quote_plus(self.search_query)
        url = f"https://www.linkedin.com/search/results/content/?keywords={encoded}"
        self.driver.get(url)
        time.sleep(2)
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 800)")
            time.sleep(1)
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")
        best, best_score = None, -1
        for p in posts:
            try:
                pid = p.get_attribute('data-urn') or p.get_attribute('id')
                if pid in (x['post_id'] for x in self.engagement_history['posts']):
                    continue
                r = p.find_element(By.XPATH, ".//button[contains(@aria-label,'reactions')]/span").text
                rc = int(''.join(filter(str.isdigit, r))) if r else 0
                c = p.find_element(By.XPATH, ".//button[contains(@aria-label,'comment')]/span").text
                cc = int(''.join(filter(str.isdigit, c))) if c else 0
                score = rc + cc
                if score > best_score:
                    best, best_score = p, score
            except Exception:
                continue
        return best

    def fetch_user_id(self):
        url = "https://api.linkedin.com/v2/userinfo"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("sub")
        return None

    def download_image(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            path = f"temp_{uuid.uuid4().hex}.jpg"
            with open(path, 'wb') as f:
                f.write(response.content)
            return path
        return None

    def upload_image(self, image_path, user_id):
        register_resp = requests.post(
            'https://api.linkedin.com/v2/assets?action=registerUpload',
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            },
            json={
                "registerUploadRequest": {
                    "owner": f"urn:li:person:{user_id}",
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "serviceRelationships": [{
                        "identifier": "urn:li:userGeneratedContent",
                        "relationshipType": "OWNER"
                    }]
                }
            }
        )
        if register_resp.status_code != 200:
            return None
        upload_data = register_resp.json()
        upload_url = upload_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset = upload_data['value']['asset']
        with open(image_path, 'rb') as f:
            upload_resp = requests.put(upload_url, headers={'Authorization': f'Bearer {self.access_token}'}, data=f)
        return asset if upload_resp.status_code in [200, 201] else None

    def create_post_api(self, text, image_asset=None):
        user_id = self.fetch_user_id()
        if not user_id:
            return False
        content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE" if image_asset else "NONE"
        }
        if image_asset:
            content["media"] = [{
                "status": "READY",
                "description": {"text": "Reposted image"},
                "media": image_asset,
                "title": {"text": "Shared Post"}
            }]
        body = {
            "author": f"urn:li:person:{user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": content
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        resp = requests.post('https://api.linkedin.com/v2/ugcPosts',
                             headers={
                                 'Authorization': f'Bearer {self.access_token}',
                                 'Content-Type': 'application/json',
                                 'X-Restli-Protocol-Version': '2.0.0'
                             },
                             json=body)
        return resp.status_code == 201

    def repost_once(self):

        self._maybe_reset_daily_counter()
        if self.posts_today >= self.max_daily_posts:
            logging.info("Daily post limit reached. Skipping post.")
            return
        import datetime
        post = self.find_top_post()
        if not post:
            return
        pid = post.get_attribute('data-urn') or post.get_attribute('id')
        try:
            actor = post.find_element(By.CSS_SELECTOR,
                                      "div.update-components-actor__meta span.update-components-actor__title span").text
        except Exception:
            actor = "Unknown"
        try:
            btn = post.find_element(By.CSS_SELECTOR, ".feed-shared-inline-show-more-text__see-more-less-toggle")
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
        except NoSuchElementException:
            pass
        try:
            body = post.find_element(By.CSS_SELECTOR,
                                     "div.feed-shared-update-v2__description span.break-words").text
        except Exception:
            body = ""

        try:
            image_element = post.find_element(By.CSS_SELECTOR, ".feed-shared-update-v2__content img")
            image_url = image_element.get_attribute("src")

        except NoSuchElementException:
            image_url = None

        print("[DEBUG] Extracted Image URL:", image_url)

        content = f"Repost from {actor}:\n\n{body}"
        content = ''.join(ch for ch in content if ord(ch) <= 0xFFFF)

        image_asset = None
        if image_url:
            image_path = self.download_image(image_url)
            user_id = self.fetch_user_id()
            if image_path and user_id:
                image_asset = self.upload_image(image_path, user_id)
                os.remove(image_path)

        if self.create_post_api(content, image_asset):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.engagement_history['posts'].append({'post_id': pid, 'author': actor, 'timestamp': now})
            self._save_history()
            self.posts_today += 1

    def close(self):
        if self.driver:
            self.driver.quit()

class BotManager:
    def __init__(self, email, password, access_token, keyword):
        self.bot = LinkedInBot(email, password, access_token, keyword)
        self.thread = None
        self.running = False

    def start(self):
        if self.running:
            return False
        self.running = True
        def target():
            self.bot.setup_browser()
            if self.bot.login():
                while self.running:
                    self.bot.repost_once()
                    time.sleep(60*60*2)  #every 2 hours
                logging.error("Failed to login")
            self.bot.close()
        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        if not self.running:
            return False
        self.running = False
        self.thread.join(timeout=5)
        return True
manager = BotManager("", "", "", "")
@app.route('/api/start_bot', methods=['POST'])
def start_bot():
    data = request.json or {}
    access_token = data.get('access_token')
    keyword = data.get('keyword')
    email = data.get('email')
    password = data.get('password')
    if not access_token or not keyword or not email or not password:
        return jsonify({'error': 'Missing access_token, keyword, email, or password'}), 400
    manager = BotManager(email, password, access_token, keyword)
    started = manager.start()
    status_code = 200 if started else 409
    return jsonify({'started': started}), status_code

@app.route('/api/stop_bot', methods=['POST'])
def stop_bot():
    
    if manager is None:
        return jsonify({'stopped': False}), 409
    stopped = manager.stop()
    status_code = 200 if stopped else 409
    return jsonify({'stopped': stopped}), status_code

if __name__ == '__main__':
    app.run(port=5000, debug=True)
