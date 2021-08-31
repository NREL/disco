FROM python:3.7-slim

USER root

RUN apt-get update \
    && apt-get install -y jq git nano tmux tree vim wget \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /data
RUN mkdir /nopt
RUN mkdir /scratch
RUN mkdir /projects
COPY docker/vimrc $HOME/.vimrc
COPY docker/setup_singularity.sh /data/setup_singularity.sh
RUN git config --global url."https://{your-token}:@github.com/".insteadOf "https://github.com/"

RUN echo "export LD_LIBRARY_PATH=/usr/lib64:/nopt/slurm/current/lib64/slurm:$LD_LIBRARY_PATH" >> $HOME/.bashrc
RUN echo "export PATH=$PATH:/nopt/slurm/current/bin" >> $HOME/.bashrc
RUN echo "slurm:x:989:989:SLURM workload manager:/var/lib/slurm:/bin/bash" >> /etc/passwd
RUN echo "slurm:x:989:" >> /etc/group

WORKDIR /repos
RUN git clone https://github.com/NREL/disco.git

RUN pip install NREL-jade

WORKDIR /repos
RUN git clone https://github.com/NREL/PyDSS.git
WORKDIR /repos/PyDSS
RUN git checkout report-metrics

RUN pip install -e .
RUN pip install -e /repos/disco

RUN touch $HOME/.profile \
    && rm -rf $HOME/.cache

WORKDIR /data
CMD [ "bash" ]
