FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8000
ENV MONGO_URL=mongodb+srv://Ravi:gycm4cge@cluster0.53r8xqg.mongodb.net/?appName=Cluster0
ENV DB_NAME=konnectra
ENV HMS_APP_ACCESS_KEY=6990826e6a127e1cf1254164
ENV HMS_APP_SECRET=BNVzVYKcn2AJkNBYu1yyrshHpBlJoRzxkY2cH6XBgkPEbXQho2SWZLipCU4e4SobDbs2mShX9oN4eZFHphhbOmFfZSi9bsHq9gKpXjPBViAZf3pBXiDmtXbmHT6NE09zSyL17WXIKOB3-t8a73rO4qZQXzsEAoz50UlYFCbelwI=

# Firebase Admin SDK — place your service account JSON in backend/ as firebase-service-account.json
ENV FIREBASE_SERVICE_ACCOUNT_KEY=/app/voicematch-7640d-firebase-adminsdk-fbsvc-7cad195cea.json

# Copy your backend code
COPY . /app

EXPOSE 8000

# Use Render's provided PORT
CMD ["sh", "-c", "gunicorn server:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
