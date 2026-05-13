FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# For a production image, uncomment the next line and remove the volume mount in docker-compose.
# COPY . .

# Source is bind-mounted in docker-compose for development (hot reload via --reload).
# entrypoint.sh runs "alembic upgrade head" before starting the server, so the
# schema is always up to date when the app starts.
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
