
# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any exact dependencies
# We use --no-cache-dir to keep the image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Define environment variables
# These can be overridden in docker-compose
ENV FRONTEND_URL=http://localhost:3000
ENV PORT=8000

# Run the application
CMD ["python", "start.py"]
