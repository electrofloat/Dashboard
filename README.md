# Dashboard  - [![Badge Kofi]][Kofi]

## Summary

This is a visually [Heimdall](https://github.com/linuxserver/Heimdall) like dashboard which uses [Authelia](https://github.com/authelia/authelia) for authentication and authorization (which can be overridden).

![Screenshot](./screenshot.png)

## Usage

### 1. Setup Docker Compose

```yaml
services:
  dashboard:
    image: matrixeler/dashboard:latest
    hostname: dashboard
    container_name: dashboard
    ports:
      - "5000:5000"
    restart: unless-stopped
    volumes:
      - user-data/:/app/user-data:ro
    healthcheck:
      disable: true
```

Persistent files reside under `user-data/`. The file structure is:

| Path                       | Type | Description                                                                                                               |
| -------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------- |
| `user-data/`                   | 📂   | holds all persistent data                                                                                                 |
| `user-data/config.yml`         | 🗎    | the config file                                                                                      |
| `user-data/backgrounds/`             | 📂   | image files to use as a background |
| `user-data/icons/`             | 📂   | image files to use as icons in the tiles  |


### 2. Configure the Dashboard

Edit the contents of `user-data/config.yml`. An example can be found [here](./dev/config.yml).
After a config change you have to restart the application.

[Kofi]: https://ko-fi.com/dexterandapps
[Badge Kofi]: https://img.shields.io/badge/KO--FI-SUPPORT-orange?style=for-the-badge&logo=ko-fi&logoSize=auto
