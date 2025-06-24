# 1. Base image
FROM python:3.9-slim

# 2. Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates curl unzip xauth \
        libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libpango-1.0-0 libpangocairo-1.0-0 libgtk-3-0 libgbm1 \
        libxcomposite1 libxrender1 libxfixes3 \
        xvfb fluxbox x11vnc net-tools nginx x11-utils && \
    rm -rf /var/lib/apt/lists/*

# 3. Install Google Chrome
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 4. Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV DISPLAY=:99

# 5. Set working directory
WORKDIR /usr/src/app

# 6. Copy app files (including entrypoint.sh, requirements.txt, backend/)
COPY . .

# 7. Install Python dependencies
RUN pip install --no-cache-dir -r ./requirements.txt

# 8. Make entrypoint executable
RUN chmod +x entrypoint.sh

# 9. Expose ports
EXPOSE 5000 10000

# 10. Start app
ENTRYPOINT ["/entrypoint.sh"]
