FROM python:3.11-slim

USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user
ENV PATH="/home/user/.local/bin:$PATH"
ENV PYTHONPATH=/home/user/app
ENV PORT=7860

WORKDIR /home/user/app

COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user config ./config
COPY --chown=user dev/backend ./dev/backend

WORKDIR /home/user/app/dev/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
