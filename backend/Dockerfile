# 1. Base image
FROM python:3.9-slim

# 2. Install Chrome and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates \
        libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libpango-1.0-0 libpangocairo-1.0-0 libgtk-3-0 libgbm1 \
        libxcomposite1 libxrender1 libxfixes3 curl unzip && \
    rm -rf /var/lib/apt/lists/* && \
    wget -qO- https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 3. Set environment for Chrome
ENV CHROME_BIN=/usr/bin/google-chrome

# 4. Create app directory and copy files
WORKDIR /usr/src/app
COPY . .

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Expose Flask port and run with Gunicorn (recommended for production)
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "linkedin_bot:app"]
