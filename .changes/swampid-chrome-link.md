---
bump: third
---
### Sign-in on the chrome is the hub's, not ours

The site nav now carries the same `swampid-link` the hub uses, pointed at
https://auth.swamplink.com/login, and loads https://swamplink.com/swampid-nav.js
once. The script is reused from the hub; Wings does not ship a copy or grow
an auth stack of its own.
