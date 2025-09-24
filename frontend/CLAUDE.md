# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a React Router v7 application with TypeScript and TailwindCSS, using server-side rendering (SSR) by default. It's a modern full-stack React application template with hot module replacement and production-ready deployment capabilities.

## Development Commands

- `npm run dev` - Start development server with HMR (available at http://localhost:5173)
- `npm run build` - Create production build
- `npm run start` - Run production server from built files
- `npm run typecheck` - Run TypeScript type checking and generate route types

## Architecture

### File Structure
- `app/` - Main application code
  - `routes/` - Route components (file-based routing)
  - `routes.ts` - Route configuration
  - `root.tsx` - Root layout component with HTML structure
  - `app.css` - Global styles and TailwindCSS imports
  - `welcome/` - Welcome page component and assets
- `public/` - Static assets
- `build/` - Generated production build (after `npm run build`)

### Key Patterns

**Routing**: Uses React Router v7 file-based routing with type-safe route definitions. Routes are defined in `app/routes.ts` and individual route files in `app/routes/`.

**Styling**: TailwindCSS v4 with custom theme configuration in `app.css`. Supports dark mode with automatic system preference detection.

**TypeScript**: Strict TypeScript configuration with path mapping (`~/*` points to `./app/*`). Route types are auto-generated.

**SSR**: Server-side rendering enabled by default via `react-router.config.ts`. Can be disabled by setting `ssr: false`.

## Configuration Files

- `react-router.config.ts` - React Router configuration (SSR settings)
- `vite.config.ts` - Vite build configuration with TailwindCSS and path resolution
- `tsconfig.json` - TypeScript configuration with strict mode and custom paths
- `Dockerfile` - Production Docker container setup

## Route Types

Routes automatically generate TypeScript types in `.react-router/types/`. Import route-specific types using the pattern:
```typescript
import type { Route } from "./+types/route-name";
```

## Deployment

Supports multiple deployment options including Docker, AWS ECS, Google Cloud Run, Azure Container Apps, and traditional Node.js hosting. The built application includes both client-side assets (`build/client/`) and server-side code (`build/server/`).