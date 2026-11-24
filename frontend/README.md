# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.

## Authentication configuration

Google sign-in requires a Google OAuth 2.0 **Web application** client ID. Configure the frontend origin (for example, `http://localhost:5173`) in the client's authorized JavaScript origins, then set the same client ID in both:

- `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`
- `backend/.env` as `GOOGLE_CLIENT_ID`

Use the placeholders in each directory's `.env.example` as a starting point, then restart both development servers. For production, configure the exact HTTPS frontend origin and the same client ID on both sides. The client ID is public configuration; never put a client secret in frontend environment variables.

Google sign-in creates standard user accounts only. It does not grant administrator or analyst roles, and it does not automatically link a Google identity to an existing local account with the same email address.
