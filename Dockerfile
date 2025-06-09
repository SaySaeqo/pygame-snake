FROM fedora:41 AS snake_build
WORKDIR /source
COPY . .
RUN dnf update -y
RUN dnf install python -y
RUN dnf install python-pip -y
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN dnf install binutils -y
RUN pyinstaller --onefile host.py

FROM fedora:41
WORKDIR /app
RUN dnf update -y
RUN dnf install binutils python python-pip -y
COPY --from=snake_build /source/dist/host .
EXPOSE 52413/tcp
EXPOSE 52413/udp
CMD ["/app/host"]