FROM python:3.11-slim-bookworm

# Install system dependencies for OpenCV and Matplotlib
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install libraries
# Note: we use tensorflow-cpu to reduce memory footprint and image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    numpy \
    opencv-python-headless \
    pillow \
    matplotlib \
    tensorflow-cpu \
    keras==3.14.1 \
    python-multipart

# Copy all project files
COPY . .

# Expose FastAPI default port
EXPOSE 8000

# Start command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
