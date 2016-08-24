FROM fabiommendes/gunicorn-django

# Enable production settings by default; for development, this can be set to
# `false` in `docker run --env`
ENV DJANGO_PRODUCTION=true

# Set terminal to be noninteractive
ENV DEBIAN_FRONTEND noninteractive

# Sets codeschool as the default application
ENV GUNICORN_WSGI_APPLICATION=codeschool.site.wsgi:application

# Install apt dependencies
RUN apt-get update \
	&& apt-get install --no-install-recommends --no-install-suggests -y \
            build-essential \
            gcc \
            g++ \
            python \
            python3-pip \
            python3-pil \
            python3-numpy \
            python3-matplotlib \
            python3-pandas \
            ruby \
            tcc \
	&& rm -rf /var/lib/apt/lists/*


# Copy files and data
ADD . /codeschool
WORKDIR /codeschool

RUN pip3 install -r requirements.txt \
    && pip3 install pytuga

# Expose ports
# 80 = Nginx
# 8000 = Gunicorn
EXPOSE 80 8000
