# nextcloud-aio
My implementation of Nextcloud's All-in-One Docker Image, running on Docker Desktop for Mac OS X, using Caddy as the reverse proxy. 

# Introduction
Ok, I've been trying all week to try and get nextcloud aio running and I finally got it today. I previously had Nextcloud 25 running behind Traefik 2 using docker-compose on Mac OS X Catalina, but I knew I needed to upgrade. This was painful, as there are some things that aren't documented in the readme and I only got vey lucky after reading about a million help posts. Eventually, I'll ditch Mac OS X and transition to a machine running Ubuntu natively. But, for now, enough things have changed I've spent enough time working on it and this will do. 


# Setup
- Cloudflare domain
 -- Created "A" DNS record with the Cloudflare proxy feature on
- Mac mini is the server running OS X Catalina
- Reverse proxy desired for automatic SSL renewal 
- I'm fine to rebuild my database from scratch (i.e., upload files into the data directors and have Nextcloud rescan the files (more specifics on that later).

- I really like the elegance of docker compose, so I am using the following *.yml file

```
# filename: nc-aio-caddy.yml
# version: "3.8" # obsolete now

services:
  caddy:
    image: caddy:cloudflaredns
    restart: unless-stopped
    container_name: caddy
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./certs:/certs
      - ./config:/config
      - ./data:/data
      - ./sites:/srv
    ports:
      - "443:443"
      - "80:80"
    #network_mode: "host" # IMPORTANT: incompatible with docker desktop, blocks 443. Instead, in the Caddyfile, use `reverse_proxy host.docker.internal:11001`

  nextcloud:
    image: nextcloud/all-in-one:latest
    restart: unless-stopped
    container_name: nextcloud-aio-mastercontainer
    ports:
      - "8080:8080"
      - "3478:3478"
      - "8443:8443"
    environment:
      - APACHE_PORT=11001
      - APACHE_IP_BINDING=0.0.0.0
      #- SKIP_DOMAIN_VALIDATION=true
      #- NEXTCLOUD_DATADIR=/Volumes/Nextcloud/Nextcloud-AIO # this is where I want my data
    volumes:
      - nextcloud_aio_mastercontainer:/mnt/docker-aio-config
      - /var/run/docker.sock.raw:/var/run/docker.sock:ro

volumes:
  nextcloud_aio_mastercontainer:
    name: nextcloud_aio_mastercontainer

```

My Caddyfile is (make sure you get the API_TOKEN, not the API_KEY):

```
#filename: Caddyfile
https://nextcloud.mydomain.net:443 {
        tls { 
              dns cloudflare <APITOKEN>
              }        
        header Strict-Transport-Security max-age=31536000;
        #reverse_proxy nextcloud-aio-domaincheck:11001 # this won't resolve and you'll get a cryptic 502 error from caddy
        reverse_proxy host.docker.internal:11001 # 11001 just for kicks, bc 11000 wasn't working
}
```

The caddy:cloudflaredns image was built using the following Dockerfile:

```
# filename: caddyDockerfile
FROM caddy:2-builder-alpine AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare

FROM caddy:2-alpine

RUN apk add curl
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

Build this with: 

` docker build -t caddy:cloudflaredns -f caddyDockerfile .`

- Finally, call the docker-compose with:
 
`docker compose -f nc-aio-caddy.yml up --force-recreate --build`

# Things I learned 

- Docker desktop has some pretty serious limitations. The most serious is the inability to run any container in network_mode: "host" [source](https://stackoverflow.com/questions/55851632/docker-compose-network-mode-host-not-working). The network_mode: host doesn't work on Mac OS X or Windows, so, according to [this source](https://stackoverflow.com/questions/55851632/docker-compose-network-mode-host-not-working), I reverse_proxy incoming 443 packets to host.docker.internal:11001 in my Caddyfile. This should work, but the caddy container refuses to see port 11001 on host.docker.internal ("nc -z host.docker.internal 11001; echo$?" returns "1").  However, "nc -z host.docker.internal 8080; echo $?" returns 0, and it can also see the other ports I've published in the docker-compose script. I suspect the reason I can't see 11001 from inside the caddy container is because the AIO image spins up the apache container at the very end of the setup, so the port is not published (or has no valid endpoint) until then. 

- In spite of caddy being "easy", the configuration can still be finicky. I started [here] (https://samjmck.com/en/blog/using-caddy-with-cloudflare/) and ended up using the Letsencrypt method, which required me to roll my own caddy image with the [cloudflare dns plugin](). I didn't trust anyone's prebuilt images, since we're talking about access to my personal data, so I chose to roll my own. 

- Nextcloud AIO takes its sweet time about downloading containers and then starting them up the first time. I mean, like, go grab a coffee or beer and come back in an hour. I even saw some weird errors (like processes dying off) in the log file, and caddy threw some "connection refused" errors. Nextcloud-aio-nextcloud was unhealthy (via `docker ps`) for a very long time, but it eventually righted itself. All the while, if you're only looking at the web interface, the throbber spins and you have no clue as to what's going on. That's why I let the log run in a terminal window (by leaving out the `-d` switch in my `docker-compose up` command). So, patience is a virtue here.

- Make sure you get a **really** clean start. If you try to run the docker-compose script and your toddler accidentally presses `ctrl+c`, go through the steps to [properly reset](https://github.com/nextcloud/all-in-one#how-to-properly-reset-the-instance) the instance. At some point, I considered making a bash script to do all this automatically, but I didn't want to spend time going down that rabbit hole, as it *would not* be a one-liner.

- According to this [source](https://caddy.community/t/v2-caddyfile-problem-with-cloudflare-plugin/7886), you should use the Cloudflare API_TOKEN not the API_KEY!

# Bonus content: A Simple Caddy Container

- I had to start somewhere, so I built the basic Caddy docker image below to prove my container could serve up valid SSL certs. That should work if you spin it up, meaning you can see the response ("Hi") on a secure page when you visit your site (https://nextcloud.mydomain.net), with no self-signed cert errors.  


```
version: '3.8'

services:
  caddy:
    image: caddy:cloudflaredns
    ports:
      - "8080:8080"
      - "80:80"
      - "443:443"
    volumes:
      - ./certs:/certs
      - ./Caddyfile:/etc/caddy/Caddyfile
```

with the following Caddyfile:

```
https://nextcloud.mydomain.net:443 {
        tls {
                dns cloudflare <APITOKEN>
        }
        respond "Hi"
}
```


# Rebuilding my database
- Finally, since my database was destroyed in the complexity of the previous standalone version's upgrade method, but my data was safe and sound on a local drive, I needed to rebuild my database. We can do this in two steps. 

- First, I copy data from my old data location (/Volumes/Nextcloud/whereverdatais) to the new location (/Volumes/Nextcloud-AIO/user/files/) with:

`rsync -avz /Volumes/Nextcloud/whereverdatais /Volumes/Nextcloud-AIO/user/files`

- Then, you need to tell Nextcloud to rescan the files. From a terminal on the host, type:

`docker exec -i --user 33 nextcloud-aio-nextcloud /bin/bash -c "php occ files:scan --all"`

Even with a bunch of files, that databasing happens fast. Postgresql is pretty cool that way. 

- Then, you can reload your website and **boom** start enjoying your files! 
