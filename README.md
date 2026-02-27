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

## Deployment (Coolify)
If you deploy this repository on Coolify:
- Check **"Is it a static site?"** in the settings.
- Set **"Publish Directory"** to `dist`.
- Set **"Build command"** to `npm run build`.
- The included `nixpacks.toml` will automatically configure the server to support React Router SPA routing.
