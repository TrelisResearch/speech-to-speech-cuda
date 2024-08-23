FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel

ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

# Install packages
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install flash-attn --no-build-isolation
RUN pip install hf_transfer

COPY . .
