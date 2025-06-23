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

# 3. Set Chrome environment
ENV CHROME_BIN=/usr/bin/google-chrome

# 4. Set working directory
WORKDIR /usr/src/app

# 5. Copy backend folder contents
COPY backend/ ./backend/

# 6. Install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# 7. Expose port and run
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "backend.linkedin_bot:app"]
