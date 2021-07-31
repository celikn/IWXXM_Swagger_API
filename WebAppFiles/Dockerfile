FROM centos/python-38-centos7
## Source: https://hub.docker.com/r/gpmidi/centos-6.5
WORKDIR /tmp/src
ADD .  /tmp/src
USER root
RUN wget https://github.com/NOAA-MDL/GIFTs/archive/refs/heads/master.zip -O GIFTs.zip
RUN unzip GIFTs.zip
RUN cp -r GIFTs-master GIFTs
RUN rm -r GIFTs-master
RUN pip install -r requirements.txt
RUN cd GIFTs &&\ 
    python setup.py install &&\ 
    cd ..
CMD ["python", "app.py"]