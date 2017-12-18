FROM python:3

WORKDIR /usr/src/app

COPY . .
RUN python install.py

CMD [ "python", "./manage.py", "test" ]
