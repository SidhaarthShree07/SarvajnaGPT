# frontend

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```

After building, the backend (FastAPI) will serve the static files from `frontend/dist` at its root path.

If the backend is running:

```powershell
cd backend; uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open app (served by backend) at: http://192.168.29.53:8000

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```
