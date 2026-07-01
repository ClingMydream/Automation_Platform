# Deployment Notes

The production directory is `/opt/automation-platform`.

Basic flow:

```bash
bash deploy/scripts/init_server.sh
cp .env.example .env
vi .env
bash deploy/scripts/deploy.sh
```

Only TCP `22` and `80` should be open on the server and in the cloud security group.

If `fail2ban` is not available in the OpenCloudOS repositories, the init script continues with `firewalld` enabled. Add an EPOL/EPEL-compatible repository later if you want SSH ban rules.
