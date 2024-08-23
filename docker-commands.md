# Docker Commands

## Build Docker Image
# Step 1: Build the Docker image
```bash
docker build -t trelis/speech-to-speech:2.1.0 .
```

# Step 2: Tag the Docker image (optional if you already tagged it in the build command)
```bash
docker tag trelis/speech-to-speech:2.1.0 trelis/speech-to-speech:latest
```

# Step 3: Push the Docker image to Docker Hub
```bash
docker push trelis/speech-to-speech:2.1.0
docker push trelis/speech-to-speech:latest
```