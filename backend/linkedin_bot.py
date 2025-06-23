import time
import os, uuid, logging, requests, json, threading
from urllib.parse import urlencode, quote_plus
from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import undetected_chromedriver as uc

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:3000",
    "https://linkedin-repost-live-lcsf.vercel.app",
    "https://linkedin-repost-live-lcsf-6ic9b33ji-adnans-projects-fce256b2.vercel.app"
]}})

logging.basicConfig(level=logging.DEBUG)

CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
SCOPES = 'profile email w_member_social openid'
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
    auth_url = 'https://www.linkedin.com/oauth/v2/authorization?' + urlencode(params)
    return jsonify({'authUrl': auth_url})

@app.route('/api/exchange_token', methods=['POST'])
def exchange_token():
    data = request.json or {}
    code = data.get('code')
    state = data.get('state')

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

    if token_resp.status_code != 200:
        return jsonify({'error': 'Failed to get token', 'details': token_resp.text}), 400

    token_data = token_resp.json()
    access_token = token_data.get('access_token')

    profile_resp = requests.get(
        'https://api.linkedin.com/v2/me?projection=(id,localizedFirstName,localizedLastName,profilePicture(displayImage~:playableStreams))',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    profile = profile_resp.ok and profile_resp.json()

    email_resp = requests.get(
        'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))',
        headers={'Authorization': f'Bearer {access_token}'}
    )
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

    def setup_browser(self):
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0")
        self.driver = uc.Chrome(options=options, headless=False)
        self.wait = WebDriverWait(self.driver, 120)

    def login(self):
        self.driver.get("https://www.linkedin.com/login")
        print("🔒 Please log in manually in the browser window.")
        print("⌛ Waiting for login to complete...")

        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "global-nav")))
            logging.info("Login successful.")
            return True
        except TimeoutException:
            logging.error("Login not completed.")
            return False

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
                logging.info("Bot logged in manually. Ready for further actions.")
                while self.running:
                    time.sleep(60*60*2)
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
    global manager
    manager = BotManager(email, password, access_token, keyword)
    started = manager.start()
    status_code = 200 if started else 409
    return jsonify({'started': started}), status_code

@app.route('/api/stop_bot', methods=['POST'])
def stop_bot():
    global manager
    if manager is None:
        return jsonify({'stopped': False}), 409
    stopped = manager.stop()
    status_code = 200 if stopped else 409
    return jsonify({'stopped': stopped}), status_code

if __name__ == '__main__':
    app.run(port=5000, debug=True)
