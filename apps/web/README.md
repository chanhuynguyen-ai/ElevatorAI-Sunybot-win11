# ElevatorAI-Web

React/Vite web interface extracted from the ElevatorAI system. It includes the home screen, floor calling, customer assistant, SOS flow and maintenance/CV console.

## Development

```bash
npm ci
cp .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL` to the Platform gateway (default `http://localhost:8000`).

## Production

The included multi-stage Dockerfile builds the Vite app and serves it through Nginx. In the full `ElevatorAI-Platform`, Nginx proxies API calls to the gateway so the browser can use a single origin.

The checked-in `dist/` from the legacy repository is intentionally not retained; builds are reproducible from `src/` + `package-lock.json`.
