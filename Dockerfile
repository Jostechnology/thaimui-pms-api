# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.9-slim-bullseye

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1 


# Install pip requirements
RUN apt-get update
RUN apt-get install python3-dev default-libmysqlclient-dev gcc  -y
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
WORKDIR /
COPY . /
ARG ENV 
ADD ${ENV} ./
EXPOSE 5000
# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
# RUN useradd appuser && chown -R appuser /
# USER appuser

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
ENTRYPOINT ["/entrypoint.sh"]
