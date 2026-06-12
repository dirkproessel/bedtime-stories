# React + Supabase Starter Template

A modern, production-ready starter template for React applications.

## Included Technologies
- **Vite** (Build Tool)
- **React 19**
- **Tailwind CSS v4**
- **Supabase** (Pre-configured Client)
- **Zustand** (State Management)
- **React Router**
- **Coolify / Nixpacks** ready (SPA support built-in)

## How to use

1. Clone or click "Use this template" on GitHub
2. Run `npm install`
3. Copy `.env.example` to `.env.local` and add your Supabase details
4. Run `npm run dev` to start developing locally

## Deployment (Coolify & VPS Live-Setup)
Dieses Projekt läuft live auf einem **VPS** und wird automatisch bei Pushs auf GitHub über **Coolify** neu gebaut und deployed.

Konfiguration in Coolify:
- Check **"Is it a static site?"** in den Einstellungen.
- Setze **"Publish Directory"** auf `dist`.
- Setze **"Build command"** auf `npm run build`.
- Die im Projekt enthaltene `nixpacks.toml` sorgt automatisch dafür, dass das SPA-Routing korrekt funktioniert.
