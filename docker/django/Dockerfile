FROM debian:jessie

# Install apt and pip dependencies
RUN apt-get update \
	&& apt-get install --no-install-recommends --no-install-suggests -y \
            python3 \
            python3-pip \
	&& rm -rf /var/lib/apt/lists/* \
	&& mkdir pip-cache \
	&& pip3 install --cache-dir pip-cache \
	        django \
	        gunicorn \
    && rm pip-cache
RUN pip3 install -r requirements.txt

# Expose ports
# 80 = Nginx
# 8000 = Gunicorn
EXPOSE 80 8000

# Entry point
CMD ["gunicorn", "-c", "gunicorn_conf.py", "--chdir", "src", "codeschool.site.wsgi:application", "--reload"]