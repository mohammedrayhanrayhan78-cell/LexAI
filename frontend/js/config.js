/**
 * config.js — single source of truth for the backend base URL.
 *
 * In development (served by nginx on port 80), nginx proxies /api/ to the
 * backend container so an empty string "" means "same origin" and works
 * without hardcoding localhost.
 *
 * To point at a different host (e.g. during local dev without Docker) set:
 *   window.LEXAI_API_BASE = "http://localhost:8000"
 * in a <script> tag before loading the modules, OR change the constant below.
 */
export const API_BASE =
  (typeof window !== "undefined" && window.LEXAI_API_BASE) ||
  "";  // empty = same origin (nginx proxy)

