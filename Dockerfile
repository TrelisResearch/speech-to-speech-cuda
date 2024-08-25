FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel

ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

# Install packages
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN apt-get update
RUN apt-get install -y
RUN apt-get install build-essential gcc -y
RUN apt-get install portaudio19-dev -y
RUN pip install uv
RUN uv pip install --no-cache-dir -r requirements.txt
RUN uv pip install flash-attn --no-build-isolation
RUN uv pip install hf_transfer numpy scipy pyaudio


COPY . .
