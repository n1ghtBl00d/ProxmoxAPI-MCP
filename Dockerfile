# Use an official Python runtime as a parent image
FROM python:3

# Set the working directory in the container
WORKDIR /app

# --- Dependency Installation ---

# Copy the requirements file into the container at /app
# This is done first to leverage Docker layer caching
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir prevents pip from storing the cache, reducing image size
# --upgrade pip ensures we have the latest pip version
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Application Code ---

# Copy the rest of the application code into the container at /app
# Files listed in .dockerignore will be excluded
COPY . .

# --- Environment Variables ---

# NOTE: The .env file is NOT copied by default due to .dockerignore.
# Proxmox credentials and settings should be passed as environment variables
# when running the container, for example:
# docker run -e PROXMOX_HOST=... -e PROXMOX_USER=... -e PROXMOX_PASSWORD=... <image_name>

# --- Run the Application ---

# Define the command to run your application
# This will execute proxmox_mcp.py using the Python interpreter
CMD ["python", "proxmox_mcp.py"]
