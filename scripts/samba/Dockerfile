FROM ubuntu:24.04

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends samba samba-vfs-modules \
 && rm -rf /var/lib/apt/lists/* \
 && if getent passwd ubuntu >/dev/null; then \
      usermod -l hqadmin ubuntu && groupmod -n hqadmin ubuntu; \
    else \
      groupadd -g 1000 hqadmin && useradd -u 1000 -g hqadmin -M -s /usr/sbin/nologin hqadmin; \
    fi \
 && mkdir -p /home/hqadmin/kcw-files \
 && chown hqadmin:hqadmin /home/hqadmin/kcw-files

COPY smb.conf /etc/samba/smb.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && testparm -s >/dev/null

EXPOSE 445/tcp
ENTRYPOINT ["/docker-entrypoint.sh"]
