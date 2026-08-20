# sets the base image here -slim tag mean Docker use highly optimized sys image
FROM python:3.12-slim
# sets the working directory to /app
WORKDIR /app

# copies the mentioned versions in .txt
COPY requirements.txt .
# installs my application dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copies rest of the file tree
COPY . .

# default startup command
CMD ["python", "app.py"]

# Dockerfile is the blueprint for the Docker container image, 
# container img is lightweight, executable package that contains all codes, dependencies, runtime, system tools required to run a software 

# Every time Docker builds your app, it follows this recipe from the top.