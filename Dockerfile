FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]