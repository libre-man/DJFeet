from python:3

RUN mkdir /home/dj_feet


ADD ./docker_ssh /home/dj_feet/
ADD ./docker_ssh.pub /home/dj_feet/

RUN apt-get -y update && \
    apt-get install -y git python3-pip python3-numpy openssh-client

RUN eval $(ssh-agent -s) && \
    ssh-add /home/dj_feet/docker_ssh && \
    rm /home/dj_feet/docker_ssh* && \
    mkdir -p ~/.ssh && \
    [ -f /.dockerenv ] && \
    printf "Host *\n\tStrictHostKeyChecking no\n\n" > ~/.ssh/config && \
    git clone -b 14-dockerize-djfeet git@gitlab.com:SilentDiscoAsAService/DJFeet.git /home/dj_feet/DJFeet

RUN cd /home/dj_feet/DJFeet && \
    make setup && \
    pip3 install gunicorn

RUN cd /home/dj_feet/DJFeet && \
    python3 setup.py install

RUN apt-get install -y libav-tools

CMD cd /home/dj_feet/DJFeet && gunicorn -w 1 dj_feet.wsgi:app
