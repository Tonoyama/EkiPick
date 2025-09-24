import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("/chat", "routes/chat.tsx"),
  route("/properties", "routes/properties.tsx"),
  route("/auth/callback", "routes/auth.callback.tsx"),
  route("/explore", "routes/explore.tsx"),
  route("/pins", "routes/pins.tsx"),
  route("/hazard-map", "routes/hazard-map.tsx"),
] satisfies RouteConfig;
