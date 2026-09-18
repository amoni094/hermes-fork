# ProtonVPN Melbourne Physical Servers

Last updated: Aug 2026. Re-parse serverlist.json periodically (see SKILL.md for the command).

72 Melbourne logical servers share 4 distinct physical IPs/pubkeys.
All use port 443. These are the pairs to put in the SERVERS=() array.

## Current pairs (ordered by load at time of setup)

| IP             | X25519 Public Key                                  | Notes               |
|----------------|----------------------------------------------------|---------------------|
| 144.48.38.98   | FgeJr7RyQiEKpXVchUYzFsB7p6Ir8fJAA/LqATLjfgY=     | lowest load (~37%)  |
| 103.108.229.18 | 22eXRgMiS/iVgGxxksbmlk1JDgFoV7RXPvGLuaCOPiY=     |                     |
| 144.48.38.178  | enwR3M+w4F/8bBPz85kf46hh/dVSmQfeoQnECaLo1lo=     | current (AU#291)    |
| 79.127.155.65  | DBGcLTkmP+P/0coBrPtXWst9JvST4cufH3KH6h1rFyk=     |                     |

## SERVERS=() array for protonvpn-fallback.sh

Put the currently active server first (so it gets skipped on failover, tried last as rescue):

```bash
SERVERS=(
  "enwR3M+w4F/8bBPz85kf46hh/dVSmQfeoQnECaLo1lo=|144.48.38.178:443"
  "FgeJr7RyQiEKpXVchUYzFsB7p6Ir8fJAA/LqATLjfgY=|144.48.38.98:443"
  "22eXRgMiS/iVgGxxksbmlk1JDgFoV7RXPvGLuaCOPiY=|103.108.229.18:443"
  "DBGcLTkmP+P/0coBrPtXWst9JvST4cufH3KH6h1rFyk=|79.127.155.65:443"
)
```
