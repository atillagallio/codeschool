FROM python:3.5
ADD . /src
WORKDIR /src
RUN pip3 install -r requirements.txt
EXPOSE 8000
CMD gunicorn codeschool.site.wsgi -b 8000