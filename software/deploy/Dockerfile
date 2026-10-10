FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml .
COPY ball_demo ./ball_demo
RUN pip install --no-deps .
ENV BALL_DATA_DIR=/data
EXPOSE 8080
CMD ["python", "-m", "ball_demo.cli", "serve", "--host", "0.0.0.0", "--port", "8080"]
