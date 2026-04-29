# Creative Pipeline PoC Deployment Report

## Live Demo

The short-form demo is running at:

```text
http://101.47.30.171
```

Current app:

```text
agent-pipeline/app_short.py
```

Current serving model:

```text
Client browser -> BytePlus ECS public IP:80 -> Streamlit app directly
```

Nginx is not required for the current PoC setup. Streamlit is bound directly to public port `80`.

## How To Verify The Deployment

On the ECS server:

```bash
sudo ss -tlnp | grep :80
systemctl status vlm-demo --no-pager
systemctl status nginx --no-pager
```

Expected:

```text
0.0.0.0:80 users:(("streamlit",...))
vlm-demo active
nginx inactive
```

From a client machine:

```bash
curl -I http://101.47.30.171
curl -s http://101.47.30.171/_stcore/health
```

Expected:

```text
HTTP/1.1 200 OK
ok
```

## Proxy Issue Found During Deployment

The app and ECS server were working, but the browser appeared to hang forever.

Server checks passed:

```bash
curl -I http://101.47.30.171
curl -s http://101.47.30.171/_stcore/health
```

The Streamlit WebSocket check also passed:

```text
HTTP/1.1 101 Switching Protocols
```

The actual issue was the browser/proxy path. Chrome was using a proxy or managed network setting that intercepted raw-IP HTTP traffic. In Chrome DevTools, the request showed:

```text
Provisional headers are shown
```

This means Chrome started the request but did not receive response headers. The ECS and Streamlit app were not the root cause.

The workaround was to launch Chrome without proxy:

```bash
open -na "Google Chrome" --args --no-proxy-server --user-data-dir=/tmp/chrome-no-proxy
```

After opening the demo in that no-proxy Chrome window, the app loaded correctly.

## Client Access Guidance

For this PoC/demo, clients can access:

```text
http://101.47.30.171
```

If a client sees a blank page, spinning loader, gateway timeout, or host-not-found message, their corporate proxy/VPN may be blocking raw public IP HTTP traffic.

Recommended checks:

1. Try another browser.
2. Try incognito/private mode.
3. Disable VPN/proxy temporarily.
4. Try a non-corporate network or mobile hotspot.
5. On macOS Chrome, launch without proxy:

```bash
open -na "Google Chrome" --args --no-proxy-server --user-data-dir=/tmp/chrome-no-proxy
```

For a more reliable prospect-facing setup later, use a real domain name and HTTPS. Raw IP HTTP is often intercepted or blocked by enterprise proxies.

## How The Demo Works

1. Client opens:

```text
http://101.47.30.171
```

2. The app asks for the client's BytePlus Ark API key.

3. The key is kept in the Streamlit browser session. It is not hardcoded into the app.

4. Client uploads a marketing video.

5. The app runs the creative pipeline:

```text
Video upload
-> Seed 2.0 Pro analysis
-> Compliance and performance critique
-> Improved storyboard
-> Seedance-ready video prompt
-> Optional reference image generation
-> Final video generation
-> QA check on generated video
```

6. Usage and estimated cost are shown in the sidebar.

## Operations Commands

Check app service:

```bash
systemctl status vlm-demo --no-pager
```

Restart app:

```bash
systemctl restart vlm-demo
```

Watch logs:

```bash
journalctl -u vlm-demo -f
```

Check local health from ECS:

```bash
curl -s http://127.0.0.1/_stcore/health
```

Check which process owns port `80`:

```bash
sudo ss -tlnp | grep :80
```

## Current Systemd Service

The demo runs as a systemd service named:

```text
vlm-demo
```

The service launches:

```text
/opt/vlm-creative-pipeline/.venv/bin/streamlit run agent-pipeline/app_short.py --server.address 0.0.0.0 --server.port 80 --server.headless true --server.enableCORS false --server.enableXsrfProtection false --browser.gatherUsageStats false
```
