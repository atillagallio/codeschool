# We base on debian:jessie instead of python:3.4 to use the Python version found
# on apt. This makes the container lighter. Sub-containers also benefit from
# using apt.
FROM debian:jessie

ENV GUNICORN_WSGI_APPLICATION=test_project.wsgi

# Install apt and dependencies
RUN apt-get update \
	&& apt-get install --no-install-recommends --no-install-suggests -y \
            python3 \
            python3-pip \
	&& rm -rf /var/lib/apt/lists/*


# Install django and gunicorn from pip in order to use the latest versions
RUN pip3 install django \
    && pip3 install gunicorn


# Copy gunicorn conf
ADD . /django-base
WORKDIR /django-base

# Expose ports
EXPOSE 8000:8000

# Entry point
CMD gunicorn -c /django-base/gunicorn_conf.py $GUNICORN_WSGI_APPLICATION --reload