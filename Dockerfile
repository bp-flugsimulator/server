FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN python install.py

COPY . .

CMD [ "python", "./manage.py", "test" ]
